# test_crawl_and_celebrity.py

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import wikipedia
from bs4 import BeautifulSoup
import json

# ───────────────────────────────────────────────────────────────────
# 환경 변수에서 CHROMEDRIVER_PATH 불러오기
# ───────────────────────────────────────────────────────────────────
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")

WEBSITES = {
    "SIGNAL_BZ": "https://signal.bz/"
}

# ───────────────────────────────────────────────────────────────────
# 1) 위키피디아 언어 설정 및 인물 판별 함수
# ───────────────────────────────────────────────────────────────────
wikipedia.set_lang('ko')  # 한글 위키백과 사용

def fetch_wikipedia_person_info(name: str) -> dict:
    """
    name: 예) "이재명 대통령", "추성훈 야노시호 부부싸움" 등 문구 전체
    1) wikipedia.search(name) → 가장 유사한 페이지 제목 얻기
    2) wikipedia.page(candidate_title) → 페이지 객체 얻기
    3) 페이지 HTML 파싱 → infobox(class="infobox_v2" or "infobox") 내에 “직업”/“출생” 필드 확인
    4) 페이지가 인물용이면 exists=True, occupation과 summary 정보 반환
    5) 아닐 경우 exists=False 반환
    """
    result = {"exists": False}

    try:
        search_results = wikipedia.search(name, results=1)
    except Exception:
        return result

    if not search_results:
        return result

    candidate_title = search_results[0]
    try:
        page = wikipedia.page(candidate_title, auto_suggest=False)
    except (wikipedia.DisambiguationError, wikipedia.PageError):
        return result

    html = page.html()
    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.find("table", {"class": ["infobox_v2", "infobox"]})
    if not infobox:
        return result

    is_person = False
    occupation_text = ""
    for th in infobox.find_all("th"):
        header = th.text.strip()
        if header in ("직업", "직업(Occupation)", "출생", "출생일", "출생/사망"):
            is_person = True
            if header.startswith("직업"):
                td = th.find_next_sibling("td")
                if td:
                    occupation_text = td.get_text(separator=", ").strip()
            break

    if not is_person:
        return result

    summary = page.summary
    result.update({
        "exists": True,
        "page_title": page.title,
        "url": page.url,
        "summary": summary[:200] + "..." if len(summary) > 200 else summary,
        "occupation": occupation_text
    })
    return result


# ───────────────────────────────────────────────────────────────────
# 2) Selenium을 이용한 Signal.bz 크롤러
# ───────────────────────────────────────────────────────────────────
def init_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=ko-KR")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def crawl_signal_bz(driver):
    """
    Signal.bz 실시간 검색어 크롤링
    """
    url = WEBSITES["SIGNAL_BZ"]
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rank-text"))
        )
        print("[Debug] Signal.bz - '.rank-text' appeared in DOM")
    except Exception as e:
        print("[Debug] Signal.bz - Timeout waiting for .rank-text:", e)
        return []

    items = []
    try:
        title_elems = driver.find_elements(By.CSS_SELECTOR, ".rank-text")
        num_elems   = driver.find_elements(By.CSS_SELECTOR, ".rank-num")
        print(f"[Debug] Signal.bz - titles found: {len(title_elems)}, nums found: {len(num_elems)}")

        for title_elem, num_elem in zip(title_elems, num_elems):
            title_text = title_elem.text.strip()
            views = 0
            comments = 0
            if title_text:
                items.append((title_text, views, comments))
    except Exception as e:
        print(f"[Crawl Error - Signal.bz] {e}")

    return items


# ───────────────────────────────────────────────────────────────────
# 3) 메인: 크롤링 → 위키피디아 인물 판별 → 결과 JSON으로 저장 및 출력
# ───────────────────────────────────────────────────────────────────
def main():
    driver = init_chrome_driver()
    try:
        signal_items = crawl_signal_bz(driver)
    finally:
        driver.quit()

    results = []
    for title, views, comments in signal_items:
        print(f"\n--- 처리 시작: '{title}' ---")
        info = fetch_wikipedia_person_info(title)
        if not info.get("exists"):
            print(f"❌ '{title}' → 위키피디아에서 인물 페이지 없음")
            results.append({
                "keyword": title,
                "is_person": False,
                "page_title": None,
                "url": None,
                "occupation": None,
                "summary": None
            })
        else:
            print(f"✅ '{title}' → 위키피디아: {info['page_title']}")
            print(f"   • 직업: {info['occupation'] or '(직업 정보 없음)'}")
            results.append({
                "keyword": title,
                "is_person": True,
                "page_title": info["page_title"],
                "url": info["url"],
                "occupation": info["occupation"],
                "summary": info["summary"]
            })

    # 결과를 JSON 파일로 저장
    with open("test_crawl_and_celebrity_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\n[완료] 결과가 'test_crawl_and_celebrity_results.json'에 저장되었습니다.")

if __name__ == "__main__":
    main()
