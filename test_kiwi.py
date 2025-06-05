# test_kiwi_pipeline.py

import wikipedia
import requests
from bs4 import BeautifulSoup
from kiwi import Kiwi

# ───────────────────────────────────────────────────────────────────
# 1) Kiwi 초기화 및 위키피디아 언어 설정
# ───────────────────────────────────────────────────────────────────
kiwi = Kiwi()
wikipedia.set_lang('ko')  # 한글 위키백과 사용

# ───────────────────────────────────────────────────────────────────
# 2) Kiwi로 고유명사(NNP)만 추출하는 함수
# ───────────────────────────────────────────────────────────────────
def extract_proper_nouns(text: str) -> list[str]:
    """
    Kiwi 형태소 분석 → 태그(tag) == "NNP"(고유명사)인 토큰만 뽑아 반환
    """
    tokens = kiwi.tokenize(text)
    # tokens 예시: [(word, stem, tag, start, length, score), ...]
    proper_nouns = [
        word for word, stem, tag, start, length, score in tokens
        if tag == "NNP"
    ]
    # 중복 제거하면서 순서 유지
    return list(dict.fromkeys(proper_nouns))


# ───────────────────────────────────────────────────────────────────
# 3) 위키피디아에서 해당 이름이 “사람 페이지”인지 확인 & Infobox에서 직업 추출
# ───────────────────────────────────────────────────────────────────
def fetch_wikipedia_person_info(name: str) -> dict:
    """
    name: 예) "이재명", "추성훈", "이강인" 등
    1) wikipedia.search(name) → 가장 유사한 페이지 제목 얻기
    2) 해당 페이지 로드 → HTML을 BeautifulSoup으로 파싱
    3) infobox(<table class="infobox_v2" or "infobox">) 내에
       <th>직업</th> 또는 <th>출생</th> 같은 “사람용 필드”가 있으면 True
    4) 발견된 경우 요약(summary)과 infobox의 “직업” 값을 돌려 줌
    5) 페이지가 없거나 “사람용 infobox”가 없으면 exists=False 반환
    """
    result = {"exists": False}

    try:
        search_results = wikipedia.search(name, results=3)
    except Exception:
        return result

    if not search_results:
        return result

    candidate_title = search_results[0]
    try:
        # auto_suggest=False로 정확히 candidate_title을 로드 시도
        page = wikipedia.page(candidate_title, auto_suggest=False)
    except (wikipedia.DisambiguationError, wikipedia.PageError):
        return result

    html = page.html()
    soup = BeautifulSoup(html, "html.parser")

    # 사람용 Infobox는 보통 class="infobox_v2" 또는 class="infobox"
    infobox = soup.find("table", {"class": ["infobox_v2", "infobox"]})
    if not infobox:
        return result

    is_person = False
    occupation_text = ""
    # <th>태그를 돌면서 '직업' 또는 '출생' 같은 필드가 있으면 사람 판정
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
# 4) 문장(phrase)을 통째로 받아서 “Kiwi → Wikipedia 파이프라인” 실행
# ───────────────────────────────────────────────────────────────────
def process_phrase(phrase: str) -> list[dict]:
    """
    1) Kiwi로 phrase에서 고유명사(NNP)만 추출
    2) 각 이름(name)에 대해 fetch_wikipedia_person_info 호출
       → exists=True인 경우만 results에 추가
    3) 중복 페이지(title) 필터링
    4) 결과 리스트 반환
    """
    results = []
    names = extract_proper_nouns(phrase)
    print("  [DEBUG] Kiwi로 추출된 고유명사 후보:", names)

    seen_titles = set()
    for name in names:
        info = fetch_wikipedia_person_info(name)
        if not info.get("exists"):
            continue

        if info["page_title"] in seen_titles:
            continue
        seen_titles.add(info["page_title"])

        results.append({
            "candidate": name,
            "page_title": info["page_title"],
            "url": info["url"],
            "summary": info["summary"],
            "occupation": info["occupation"] or "(직업 정보 없음)"
        })
    return results


# ───────────────────────────────────────────────────────────────────
# 5) 테스트 코드: Signal.bz 예시 문장들로 동작 확인
# ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        "이재명 대통령",
        "추성훈 야노시호 부부싸움",
        "이강인 나폴리 이적",
        "유퀴즈 해이 교수",
        "KIA 선발 네일",
    ]

    for s in samples:
        print(f"\n--- 처리 시작: '{s}' ---")
        matches = process_phrase(s)
        if not matches:
            print(f"❌ '{s}' → 위키피디아에서 인물 페이지 없음")
        else:
            for m in matches:
                cand = m["candidate"]
                print(f"✅ '{s}' 내부 후보 [{cand}] → 위키피디아: {m['page_title']}")
                print(f"   • URL: {m['url']}")
                print(f"   • 요약: {m['summary']}")
                print(f"   • 직업: {m['occupation']}")
