import re
import requests
import json
import os
import pdfkit
import shutil
import datetime
import time
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import quote
from urllib.parse import unquote
import urllib3
urllib3.disable_warnings()


ZSXQ_ACCESS_TOKEN = 'A2417DE1-D1B4-F72C-9D32-'  # 登录后Cookie中的Token
GROUP_ID = '8424258282'                                  # 知识星球中的小组ID 生财有术 1824528822 caoz 8424258282
PDF_FILE_NAME = 'caoz-all-[有图]版本.pdf'                               # 生成PDF文件的名字
# 是否下载图片 True | False 下载会导致程序变慢
DOWLOAD_PICS = True
DOWLOAD_COMMENTS = True                                    # 是否下载评论
# True-只精华 | False-全部
ONLY_DIGESTS = False
FROM_DATE_TO_DATE = False                                  # 按时间区间下载
# 最早时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
EARLY_DATE = '2017-05-25T00:00:00.000+0800'
# 最晚时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
LATE_DATE = '2018-05-25T00:00:00.000+0800'
DELETE_PICS_WHEN_DONE = False                               # 运行完毕后是否删除下载的图片
DELETE_HTML_WHEN_DONE = True                               # 运行完毕后是否删除生成的HTML
# 每次请求加载几个主题 最大可设置为30
COUNTS_PER_TIME = 20
DEBUG = False                                              # DEBUG开关
# DEBUG时 跑多少条数据后停止 需与COUNTS_PER_TIME结合考虑
DEBUG_NUM = 5
time_file="lasttime.txt"

htmls = []
num = 0
maxpage = 5
next_url = ''
page_count = 0

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
</head>
<body>
<h1>{title}</h1>
<br>{author} - {cretime}<br>
<p>{text}</p>
</body>
</html>
"""



def get_data(url):
    print("get_data,page:" +url)
    OVER_DATE_BREAK = False

    global htmls, num,page_count,next_url
    #htmls = []
    #num = 0
    # headers = {
    #   'Cookie': 'zsxq_access_token=' + ZSXQ_ACCESS_TOKEN,
    #    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'
    # }
    headers = {
        'Authorization': 'A2417DE1-D1B4-F72C-9D32-',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
        'Cookie': 'zsxq_access_token=847C0E4B-38B6-2A21-4222-'
    }

    rsp = requests.get(url, headers=headers, verify=False)
    with open('temp.json', 'w', encoding='utf-8') as f:  # 将返回数据写入temp.json方便查看
        f.write(json.dumps(rsp.json(), indent=2, ensure_ascii=False))

    with open('temp.json', encoding='utf-8') as f:
        for topic in json.loads(f.read()).get('resp_data').get('topics'):
            if FROM_DATE_TO_DATE and EARLY_DATE.strip():
                if topic.get('create_time') < EARLY_DATE.strip():
                    OVER_DATE_BREAK = True
                    break

            content = topic.get('question', topic.get(
                'talk', topic.get('task', topic.get('solution'))))

            anonymous = content.get('anonymous')
            if anonymous:
                author = '匿名用户'
            else:
                author = content.get('owner').get('name')

            cretime = (topic.get('create_time')[:23]).replace('T', ' ')

            text = content.get('text', '')
            text = handle_link(text)

            tt = re.sub(r'<[^>]*>', '', text).strip()
            tt = text.replace('\n', '<br>')
            title = str(num) + '_' + cretime[:16]+ tt[:15]

            #title = str(num) + '_' + cretime[:16]
            num += 1
            if topic.get('digested') == True and ONLY_DIGESTS:
                title = '精华-'+title
                continue 

            if DOWLOAD_PICS and content.get('images'):
                soup = BeautifulSoup(html_template, 'html.parser')
                images_index = 0
                for img in content.get('images'):
                    url = img.get('large').get('url')
                    local_url = './images/' + \
                      str(filecount) + '_' + str(num - 1) + '_' + str(images_index) + '.jpg'
                    images_index += 1
                    print("img download:"+local_url)
                    urllib.request.urlretrieve(url, local_url)
                    print("img downloaded:"+local_url)
                    img_tag = soup.new_tag('img', src=local_url)
                    soup.body.append(img_tag)
                html_img = str(soup)
                html = html_img.format(
                    title=title, text=text, author=author, cretime=cretime)
            else:
                html = html_template.format(
                    title=title, text=text, author=author, cretime=cretime)

            if topic.get('question'):
                answer_author = topic.get('answer').get(
                    'owner').get('name', '')
                answer = topic.get('answer').get('text', "")
                answer = handle_link(answer)

                soup = BeautifulSoup(html, 'html.parser')
                answer_tag = soup.new_tag('p')

                answer = '【' + answer_author + '】 回答：<br>' + answer
                soup_temp = BeautifulSoup(answer, 'html.parser')
                answer_tag.append(soup_temp)

                soup.body.append(answer_tag)
                html = str(soup)

            files = content.get('files')
            if files:
                files_content = '<i>文件列表(需访问网站下载) :<br>'
                for f in files:
                    files_content += f.get('name') + '<br>'
                files_content += '</i>'
                soup = BeautifulSoup(html, 'html.parser')
                files_tag = soup.new_tag('p')
                soup_temp = BeautifulSoup(files_content, 'html.parser')
                files_tag.append(soup_temp)
                soup.body.append(files_tag)
                html = str(soup)

            comments = topic.get('show_comments')
            if DOWLOAD_COMMENTS and comments:
                soup = BeautifulSoup(html, 'html.parser')
                hr_tag = soup.new_tag('hr')
                soup.body.append(hr_tag)
                for comment in comments:
                    comment_str = ''
                    if comment.get('repliee'):
                        comment_str = '[' + comment.get('owner').get('name') + ' 回复 ' + comment.get(
                            'repliee').get('name') + '] : ' + handle_link(comment.get('text'))
                    else:
                        comment_str = '[' + comment.get('owner').get(
                            'name') + '] : ' + handle_link(comment.get('text'))

                    comment_tag = soup.new_tag('p')
                    soup_temp = BeautifulSoup(comment_str, 'html.parser')
                    comment_tag.append(soup_temp)
                    soup.body.append(comment_tag)
                html = str(soup)

            htmls.append(html)

    # DEBUG 仅导出部分数据时使用
    '''
    if DEBUG and num >= DEBUG_NUM:
        return htmls

    if OVER_DATE_BREAK:
        return htmls
    '''
  
    next_page = rsp.json().get('resp_data').get('topics')
    if next_page:
        create_time = next_page[-1].get('create_time')
        if create_time[20:23] == "000":
            end_time = create_time[:20]+"999"+create_time[23:]
            str_date_time = end_time[:19]
            delta = datetime.timedelta(seconds=1)
            date_time = datetime.datetime.strptime(
                str_date_time, '%Y-%m-%dT%H:%M:%S')
            date_time = date_time - delta
            str_date_time = date_time.strftime('%Y-%m-%dT%H:%M:%S')
            end_time = str_date_time + end_time[19:]
        else:
            res = int(create_time[20:23])-1
            # zfill 函数补足结果前面的零，始终为3位数
            end_time = create_time[:20]+str(res).zfill(3)+create_time[23:]
        end_time = quote(end_time)
        if len(end_time) == 33:
            end_time = end_time[:24] + '0' + end_time[24:]
        next_url = start_url + '&end_time=' + end_time
        with open(time_file, 'w', encoding='utf-8') as f:  # 将返回数据写入temp.json方便查看
            f.write(end_time+"\n")
            f.write(str(filecount)+"\n")
        
        with open('urls.txt', 'a', encoding='utf-8') as f:  # 将返回数据写入temp.json方便查看
            f.write(next_url+"\n")
        # print(next_url)

        if DEBUG and num >= DEBUG_NUM:
            return htmls, next_url

        if OVER_DATE_BREAK:
            return htmls, next_url
        if  page_count>= maxpage:
            return htmls, next_url
        page_count=page_count+1
        get_data(next_url)

    return htmls, next_url


def handle_link(text):
    soup = BeautifulSoup(text, "html.parser")

    mention = soup.find_all('e', attrs={'type': 'mention'})
    if len(mention):
        for m in mention:
            mention_name = m.attrs['title']
            new_tag = soup.new_tag('span')
            new_tag.string = mention_name
            m.replace_with(new_tag)

    hashtag = soup.find_all('e', attrs={'type': 'hashtag'})
    if len(hashtag):
        for tag in hashtag:
            tag_name = unquote(tag.attrs['title'])
            new_tag = soup.new_tag('span')
            new_tag.string = tag_name
            tag.replace_with(new_tag)

    links = soup.find_all('e', attrs={'type': 'web'})
    if len(links):
        for link in links:
            title = unquote(link.attrs['title'])
            href = unquote(link.attrs['href'])
            new_a_tag = soup.new_tag('a', href=href)
            new_a_tag.string = title
            link.replace_with(new_a_tag)

    text = str(soup)
    text = re.sub(r'<e[^>]*>', '', text).strip()
    text = text.replace('\n', '<br>')
    return text


def make_pdf(htmls, filecount):
    html_files = []
    for index, html in enumerate(htmls):
        file = str(index) + ".html"
        html_files.append(file)
        with open(file, "w", encoding="utf-8") as f:
            f.write(html)

    options = {
        "user-style-sheet": "temp.css",
        "page-size": "Letter",
        "margin-top": "0.75in",
        "margin-right": "0.75in",
        "margin-bottom": "0.75in",
        "margin-left": "0.75in",
        "encoding": "UTF-8",
        "custom-header": [("Accept-Encoding", "gzip")],
        "cookie": [
            ("cookie-name1", "cookie-value1"), ("cookie-name2", "cookie-value2")
        ],
        "outline-depth": 10,
    }
    filename = str(filecount)+PDF_FILE_NAME
    try:
        print('开始生成电子书'+filename)
        pdfkit.from_file(html_files, filename, options=options)
    except Exception as e:
        print('except:', e)
        pass

    if DELETE_HTML_WHEN_DONE:
        for file in html_files:
            os.remove(file)

    print("电子书生成成功！"+filename)


if __name__ == '__main__':
    images_path = r'./images'
    if DOWLOAD_PICS:
        if os.path.exists(images_path) and DELETE_PICS_WHEN_DONE:
            shutil.rmtree(images_path)
        if not os.path.exists(images_path):
            os.mkdir(images_path)

    # 仅精华
    #start_url = 'https://api.zsxq.com/v1.10/groups/481818518558/topics?scope=digests&count=30'
    # 全部
    #start_url = 'https://api.zsxq.com/v1.10/groups/481818518558/topics?count=30'
    start_url = ''
    if ONLY_DIGESTS:
        start_url = 'https://api.zsxq.com/v1.10/groups/' + GROUP_ID + \
            '/topics?scope=digests&count=' + str(COUNTS_PER_TIME)
    else:
        start_url = 'https://api.zsxq.com/v1.10/groups/' + \
            GROUP_ID + '/topics?count=' + str(COUNTS_PER_TIME)

    url = start_url
    if FROM_DATE_TO_DATE and LATE_DATE.strip():
        url = start_url + '&end_time=' + quote(LATE_DATE.strip())

    starttime = datetime.datetime.now()
    print(starttime)

    filecount = 1
    endtime=''
    
    if os.path.exists(time_file):
        f = open(time_file)             # 返回一个文件对象
        endtime = f.readline() 
        if endtime:
            url = start_url + '&end_time=' + (endtime.rstrip("\n"))
            filecount = (int)(f.readline().rstrip("\n")) +1
        f.close()
    nextpage = ''
    # make_pdf(get_data(url))
    
    print("开始地址" + url)
    html, nextpage = get_data(url)
    print("next page:"+nextpage)
    make_pdf(html, filecount)
    filecount =  filecount+1
    while nextpage:
       
        html, nextpage = get_data(nextpage)
        make_pdf(html, filecount)
        filecount = filecount+1
        htmls = []
        num = 0
        page_count=0
        time.sleep(10)

    endtime = datetime.datetime.now()
    print(endtime)
    print((endtime - starttime).seconds)
    if DOWLOAD_PICS and DELETE_PICS_WHEN_DONE:
        shutil.rmtree(images_path)
