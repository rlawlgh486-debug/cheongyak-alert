"""
SH(서울주택도시개발공사) 공식 홈페이지의 "공고 및 공지" 게시판을 읽어와서
진짜 새 모집공고로 보이는 것만 골라내는 모듈.

⚠️ 중요: SH는 청약홈 API에 데이터를 제공하지 않아서, 공식 API가 없습니다.
   이 모듈은 SH 홈페이지(i-sh.co.kr)의 게시판 HTML을 직접 읽어오는 방식이라
   1) SH가 홈페이지 구조를 바꾸면 언제든 깨질 수 있고
   2) 목록의 "자세히 보기" 링크가 자바스크립트로 동작해서, 정확한 상세페이지
      주소를 100% 확실하게 뽑아내지 못할 수 있습니다.
   그래서 아래 코드는 "실패해도 앱이 죽지 않고, 확실하지 않은 정보는 절대
   지어내지 않는다"를 최우선 원칙으로 짰습니다. 링크를 못 찾으면 목록
   페이지로라도 연결하고, 가격·평형처럼 제목만으로 알 수 없는 정보는
   빈 값으로 두고 앱에서 "확인 필요" 문구로 대체합니다.

   실행해보고 결과가 이상하면(0건이 계속 나오거나 등) 로그를 보고
   CSS 선택자·정규식을 다시 맞춰야 할 수 있습니다.
"""

import re
import time
import logging
import hashlib
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from config import LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE = "https://www.i-sh.co.kr"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CheongyakMoaBot/1.0; +https://github.com)"}

# 게시판 3개: 주택분양 / 주택임대 / 주택매입
LIST_PAGES = [
    ("주택분양", f"{BASE}/main/lay2/program/S1T294C296/www/brd/m_244/list.do?multi_itm_seq=1"),
    ("주택임대", f"{BASE}/main/lay2/program/S1T294C297/www/brd/m_247/list.do?multi_itm_seq=2"),
    ("주택매입", f"{BASE}/main/lay2/program/S1T294C3379/www/brd/m_247/list.do?multi_itm_seq=512"),
]

# 제목에 이런 단어가 있으면 "새 모집공고"일 가능성이 높다고 판단
INCLUDE_KEYWORDS = [
    "모집공고", "입주자 모집", "분양 공고", "분양공고", "청약", "공급 공고", "공급공고",
    "임대 공고", "임대공고", "재공급공고", "재공급 공고",
]

# 제목에 이런 단어가 있으면 "새 공고가 아니라 후속 안내"라고 판단해서 제외
EXCLUDE_KEYWORDS = [
    "당첨자", "발표", "서류심사", "서류제출", "서류 제출", "결과", "재계약",
    "확장형", "설문조사", "협약", "안내드립니다", "알려드립니다", "변경 및 특약",
    "이전등기", "동호 배정", "동호수 배정", "사전방문", "정정공고 안내", "만족도",
    "채용", "입찰", "낙찰", "개찰", "수의계약 내역", "설명회 개최", "취소 안내",
]


def _judge_is_recruitment(title: str) -> bool:
    """제목만 보고 '진짜 새 모집공고'인지 스스로 판단."""
    if any(bad in title for bad in EXCLUDE_KEYWORDS):
        return False
    return any(good in title for good in INCLUDE_KEYWORDS)


def _extract_seq(raw_attr: str) -> Optional[str]:
    """onclick="goView(295,'m_241',310037,...)" 또는 href="...?seq=310037" 에서 번호 추출."""
    if not raw_attr:
        return None
    m = re.search(r"goView\(\s*\d+\s*,\s*'m_\d+'\s*,\s*(\d+)", raw_attr)
    if m:
        return m.group(1)
    m = re.search(r"[?&]seq=(\d+)", raw_attr)
    if m:
        return m.group(1)
    return None


def _parse_date(text: str) -> Optional[datetime]:
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def fetch_category(category_name: str, list_url: str, days: int = 14) -> List[Dict]:
    """게시판 하나에서 최근 N일 이내의 '새 모집공고로 보이는' 글만 추림."""
    items: List[Dict] = []
    try:
        res = requests.get(list_url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[SH:{category_name}] 목록 조회 실패: {e}")
        return items

    soup = BeautifulSoup(res.text, "html.parser")

    # 실제 목록 테이블의 각 행(tr)을 찾음. 사이트 구조가 바뀌면 이 선택자부터 확인.
    rows = soup.select("table tbody tr")
    if not rows:
        # 백업: 게시판에 흔히 쓰이는 다른 마크업 패턴도 시도
        rows = soup.select("ul.board_list li") or soup.select(".bbs_list tr")

    if not rows:
        logger.warning(f"[SH:{category_name}] 목록에서 행을 하나도 못 찾았습니다. 사이트 구조가 바뀌었을 수 있습니다.")
        return items

    cutoff = datetime.now() - timedelta(days=days)

    for row in rows:
        try:
            link_tag = row.find("a")
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            if not title:
                continue

            cells = row.find_all("td")
            date_text = ""
            for cell in cells:
                candidate = cell.get_text(strip=True)
                if _parse_date(candidate):
                    date_text = candidate
                    break
            post_date = _parse_date(date_text)

            # 날짜를 못 읽었으면 안전하게 '최근 것'으로 간주해서 다음 판단으로 넘김
            # (오래된 걸 놓치는 것보다, 날짜 파싱 실패로 다 걸러지는 게 더 나쁨)
            if post_date and post_date < cutoff:
                continue

            if not _judge_is_recruitment(title):
                continue

            raw_attr = link_tag.get("onclick", "") or link_tag.get("href", "")
            seq = _extract_seq(raw_attr)
            if seq:
                link = f"{BASE}/main/lay2/program/S1T294C295/www/brd/m_241/view.do?seq={seq}"
                verified_link = True
            else:
                # 정확한 글 주소를 못 찾으면, 지어내지 않고 게시판 목록으로 연결
                link = list_url
                verified_link = False

            items.append({
                "title": title,
                "category": category_name,
                "date": post_date.strftime("%Y-%m-%d") if post_date else "",
                "link": link,
                "verified_link": verified_link,
            })
        except Exception as e:
            logger.error(f"[SH:{category_name}] 행 하나 처리 실패(건너뜀): {e}")
            continue

    logger.info(f"[SH:{category_name}] 새 모집공고로 판단된 글 {len(items)}건")
    return items


def fetch_sh_listings(days: int = 14) -> List[Dict]:
    all_items: List[Dict] = []
    for name, url in LIST_PAGES:
        all_items.extend(fetch_category(name, url, days))
        time.sleep(0.3)
    logger.info(f"[SH] 전체 합산 {len(all_items)}건")
    return all_items


def to_app_listings(sh_items: List[Dict]) -> List[Dict]:
    """
    SH 스크래핑 결과 -> 웹앱 스키마.

    공고 제목·기관(SH)·날짜·링크는 실제로 확인된 값만 넣고,
    분양가·평형·접수기간처럼 제목 텍스트만으로는 정확히 알 수 없는 값은
    절대 추측해서 채우지 않고 비워둡니다. 대신 type을 "확인필요"로 표시해서
    앱 화면에서 "자세한 조건은 SH 홈페이지에서 확인해주세요"라고 안내하게 됩니다.
    """
    results = []
    for item in sh_items:
        uid = hashlib.md5((item["title"] + item["date"]).encode("utf-8")).hexdigest()[:12]
        results.append({
            "id": f"sh_{uid}",
            "name": item["title"],
            "agency": "SH",
            "sido": "서울",
            "gu": "",
            "addr": "서울",
            "sizes": [],
            "type": "확인필요",
            "priceMin": 0,
            "priceMax": 0,
            "deposit": 0,
            "rent": 0,
            "households": 0,
            "special": [],
            "link": item["link"],
            "rStart": item["date"],
            "rEnd": item["date"],
            "winDate": item["date"],
            "noticeDate": item["date"],
            "verifiedLink": item["verified_link"],
        })
    return results


def get_recent_sh_listings(days: int = 14) -> List[Dict]:
    return to_app_listings(fetch_sh_listings(days))
