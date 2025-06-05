# do not execute : test script
import os
import time
import datetime
import socket
import urllib.request
import json

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import wikipedia
load_dotenv()
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')


# 6/5 : added article api
def get_article_info(encText:str, max_articles: int=5) -> list:    
    encText = urllib.parse.quote(encText)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={max_articles}"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    try:
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if rescode != 200:
            print(f"Error: HTTP {rescode}")
            return []
        response_body = response.read().decode("utf-8")
        print(response_body)    # debug point
        data = json.loads(response_body)
        items = data.get("items", [])
        articles = []
        for it in items:
            # html parsing
            title_html = it.get("title", "")
            title_text = BeautifulSoup(title_html, "html.parser").get_text()

            link = it.get("link", "")
            desc_html = it.get("description", "")
            desc_text = BeautifulSoup(desc_html, "html.parser").get_text()

            pub_date = it.get("pubDate", "")
            articles.append({
                "title":title_text,
                "url":link,
                "summary":desc_text,
                "pubDate":pub_date
            })
            return articles
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        print(f"URLError : {e.reason}")
    except Exception as e:
        print(f"Unexpected error:[ {e} ]")
    return []
def main() -> None:
    articles = get_article_info("이재명", max_articles=5)
    for a in articles:
        print(f"-======제목: {a['title']}")
        print(f" url: {a['url']}")
        print(f" summary: {a['summary']}")
        print(f" pubdate: {a['pubDate']}")

if __name__ == '__main__':
    main()
