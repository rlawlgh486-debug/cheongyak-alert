import re
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config import (
    API_KEY, APT_DETAIL_ENDPOINT, APT_MODEL_ENDPOINT,
    SIDO_NORMALIZE, SPECIAL_FIELD_LABELS, LOG_FILE,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Infuser {API_KEY}"}


def _get(url: str, params: dict) -> Optional[dict]:
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        logger.error(f"API 호출 실패: {url} | {e}")
        return None


def fetch_notice_list(days: int = 14) -> List[Dict[str, Any]]:
    """최근 N일 이내 모집공고일의 APT 분양정보 목록(공고 단위)을 전부 조회."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    items: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        params = {
            "page": page,
            "perPage": per_page,
            "cond[RCRIT_PBLANC_DE::GTE]": cutoff,
        }
        logger.info(f"[APT 목록] {page}페이지 조회 중... (모집공고일 >= {cutoff})")
        data = _get(APT_DETAIL_ENDPOINT, params)
        if not data:
            break

        batch = data.get("data", [])
        items.extend(batch)

        total = data.get("totalCount", 0)
        if not batch or page * per_page >= total:
            break
        page += 1

    logger.info(f"[APT 목록] 총 {len(items)}건 조회 완료")
    return items


def fetch_model_rows(house_manage_no: str, pblanc_no: str) -> List[Dict[str, Any]]:
    """공고 하나의 주택형별 상세(분양가/평형/특별공급 세대수)를 조회."""
    params = {
        "page": 1,
        "perPage": 50,
        "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no,
        "cond[PBLANC_NO::EQ]": pblanc_no,
    }
    data = _get(APT_MODEL_ENDPOINT, params)
    if not data:
        return []
    return data.get("data", [])


def _to_int(v) -> int:
    """'1,234' 같은 문자열이나 None을 안전하게 int로 변환."""
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    cleaned = re.sub(r"[^\d]", "", str(v))
    return int(cleaned) if cleaned else 0


def _to_float(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _split_address(addr: str):
    """'서울특별시 강동구 상일동 ...' -> ('서울', '강동구')"""
    if not addr:
        return "", ""
    parts = addr.strip().split()
    if not parts:
        return "", ""
    sido_raw = parts[0]
    sido = SIDO_NORMALIZE.get(sido_raw, sido_raw[:2])
    gu = ""
    if len(parts) > 1:
        for token in parts[1:]:
            if token.endswith(("구", "군", "시")):
                gu = token
                break
    return sido, gu


def _agency_from_names(house_nm: str, bsns_mby_nm: str) -> str:
    text = f"{house_nm} {bsns_mby_nm}"
    if "SH" in text or "서울주택도시공사" in text:
        return "SH"
    if "LH" in text or "한국토지주택공사" in text:
        return "LH"
    return "민간"


def enrich_with_model(notice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """공고 1건 + 주택형별 상세를 합쳐 웹앱이 쓰는 최종 포맷으로 변환."""
    house_no = notice.get("HOUSE_MANAGE_NO", "")
    pblanc_no = notice.get("PBLANC_NO", "")
    name = notice.get("HOUSE_NM", "")
    r_start = notice.get("RCEPT_BGNDE") or ""
    r_end = notice.get("RCEPT_ENDDE") or ""
    notice_date = notice.get("RCRIT_PBLANC_DE") or ""
    win_date = notice.get("PRZWNER_PRESNATN_DE") or r_end

    if not (house_no and pblanc_no and name and r_start and r_end):
        # 접수 기간이 없으면(사전청약 등 특수 케이스) 상태 계산이 안 되므로 제외
        return None

    rows = fetch_model_rows(house_no, pblanc_no)
    time.sleep(0.15)  # API 서버 부담 완화

    sizes = []
    prices = []
    special_totals = {label: 0 for label in SPECIAL_FIELD_LABELS.values()}
    households = 0

    for row in rows:
        area = _to_float(row.get("SUPLY_AR"))
        if area:
            sizes.append(round(area))
        price = _to_int(row.get("LTTOT_TOP_AMOUNT"))
        if price:
            prices.append(price)
        households += _to_int(row.get("SUPLY_HSHLDCO")) + _to_int(row.get("SPSPLY_HSHLDCO"))
        for field, label in SPECIAL_FIELD_LABELS.items():
            special_totals[label] += _to_int(row.get(field))

    if not sizes:
        sizes = [84]  # 정보 없으면 임시값 (표시만 되고 필터링엔 영향 적음)

    sido, gu = _split_address(notice.get("HSSPLY_ADRES", ""))
    special = [label for label, cnt in special_totals.items() if cnt > 0]

    return {
        "id": f"{house_no}_{pblanc_no}",
        "name": name,
        "agency": _agency_from_names(name, notice.get("BSNS_MBY_NM", "")),
        "sido": sido,
        "gu": gu,
        "addr": notice.get("HSSPLY_ADRES", f"{sido} {gu}".strip()),
        "sizes": sorted(set(sizes)),
        "type": "매매",
        "priceMin": min(prices) if prices else 0,
        "priceMax": max(prices) if prices else 0,
        "deposit": 0,
        "rent": 0,
        "households": households,
        "special": special,
        "link": notice.get("PBLANC_URL") or notice.get("HMPG_ADRES") or "https://www.applyhome.co.kr/",
        "rStart": r_start,
        "rEnd": r_end,
        "winDate": win_date,
        "noticeDate": notice_date,
    }


def get_recent_listings(days: int = 14) -> List[Dict[str, Any]]:
    """웹앱 스키마로 변환된 최근 공고 목록 (APT/매매 중심)."""
    if not API_KEY:
        logger.error("PUBLIC_DATA_API_KEY 환경변수가 설정되지 않았습니다.")
        return []

    notices = fetch_notice_list(days=days)
    if not notices:
        return []

    results = []
    for i, notice in enumerate(notices, 1):
        try:
            item = enrich_with_model(notice)
            if item:
                results.append(item)
        except Exception as e:
            logger.error(f"공고 변환 실패 ({notice.get('HOUSE_NM','?')}): {e}")
        if i % 10 == 0:
            logger.info(f"  ...{i}/{len(notices)}건 처리 중")

    logger.info(f"최종 변환 완료: {len(results)}건")
    return results
