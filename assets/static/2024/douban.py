#! /usr/bin/env python3
# Used to generate book info for learning_to_learn.org 

import requests
from bs4 import BeautifulSoup
import re

def fetch_book_info(url):
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # 发送HTTP请求
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the page: {response.status_code}")
        return None

    # 解析HTML内容
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取书名
    title_tag = soup.find('span', property='v:itemreviewed')
    title = title_tag.text.strip() if title_tag else ""

    # 提取作者
    author_tags = soup.find_all('a', href=re.compile(r'/search/'))
    authors = ', '.join([author.text.strip() for author in author_tags]) if author_tags else ""

    # 提取图片URL
    image_tag = soup.find('img', rel='v:photo')
    image_url = image_tag['src'] if image_tag else ""

    # 提取评价
    rating_tag = soup.find('strong', class_='ll rating_num')
    rating = rating_tag.text.strip() if rating_tag else ""

    # 提取评价人数
    rating_count_tag = soup.find('span', property='v:votes')
    rating_count = rating_count_tag.text.strip() if rating_count_tag else ""

    # 提取主要内容
    summary_tag = soup.find('div', class_='intro')
    summary = summary_tag.text.strip() if summary_tag else ""

    # 提取出版社
    publisher_tag = soup.find('span', string=re.compile('出版社:'))
    publisher = publisher_tag.find_next('a').text.strip() if publisher_tag else ""

    # 提取副标题
    subtitle_tag = soup.find('span', string=re.compile('副标题:'))
    subtitle = subtitle_tag.next_sibling.strip() if subtitle_tag else ""

    # 提取原作名
    original_title_tag = soup.find('span', string=re.compile('原作名:'))
    original_title = original_title_tag.next_sibling.strip() if original_title_tag else ""

    # 提取译者
    translator_tag = soup.find('span', string=re.compile('译者'))
    if translator_tag:
        translator_tags = translator_tag.find_next_siblings('a', href=re.compile(r'/author/'))
        translators = ', '.join([translator.text.strip() for translator in translator_tags]) if translator_tags else ""
    else:
        translators = ""

    # 提取出版年
    publish_year_tag = soup.find('span', string=re.compile('出版年:'))
    publish_year = publish_year_tag.next_sibling.strip() if publish_year_tag else ""

    # 提取页数
    page_count_tag = soup.find('span', string=re.compile('页数:'))
    page_count = page_count_tag.next_sibling.strip() if page_count_tag else ""

    # 返回提取的信息
    book_info = {
        'title': title,
        'authors': authors,
        'image_url': image_url,
        'rating': rating,
        'rating_count': rating_count,
        'summary': summary,
        'publisher': publisher,
        'subtitle': subtitle,
        'original_title': original_title,
        'translators': translators,
        'publish_year': publish_year,
        'page_count': page_count
    }

    return book_info

if __name__ == "__main__":
    # 豆瓣读书页面URL列表
    book_urls = [
        "https://book.douban.com/subject/20494282/",
        "https://book.douban.com/subject/27082580/",
        "https://book.douban.com/subject/4836530/",
        "https://book.douban.com/subject/4864832/",
        "https://book.douban.com/subject/34923186/",
        "https://book.douban.com/subject/27081766/",
        "https://book.douban.com/subject/26285299/",
        "https://book.douban.com/subject/25958751/",
        "https://book.douban.com/subject/36991789/",
        "https://book.douban.com/subject/35084167/",
        "https://book.douban.com/subject/1543713/",
        "https://book.douban.com/subject/1468622/",
        "https://book.douban.com/subject/34625758/",
        "https://book.douban.com/subject/26895993/",
        "https://book.douban.com/subject/34897714/",
        "https://book.douban.com/subject/4243770/",
        "https://book.douban.com/subject/26587908/",
        "https://book.douban.com/subject/25743277/",
        "https://book.douban.com/subject/35951747/",
        "https://book.douban.com/subject/1707050/",
    ]

    # 获取并打印每个书籍的信息
    for book_url in book_urls:
        book_info = fetch_book_info(book_url)
        if book_info:
            print("- 书名: %s: %s" % (book_info['title'], book_info['subtitle']))
            print("  - 原作名: %s" % book_info['original_title'])
            print("  - 作者/译者: %s / %s" % (book_info['authors'], book_info['translators']))
            print("  - 评价: %s / %s" % (book_info['rating'], book_info['rating_count']))
            print("  - 出版: %s / %s" % (book_info['publisher'], book_info['publish_year']))
            print("  - 豆瓣链接: [[%s]]" % book_url)
