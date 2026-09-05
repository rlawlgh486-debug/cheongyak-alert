import re
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config import (
    API_KEY,
    APT_DETAIL_ENDPOINT, APT_MODEL_ENDPOINT,
    URBTY_DETAIL_ENDPOINT, URBTY_MODEL_ENDPOINT,
    RENT_DETAIL_ENDPOINT, RENT_MODEL_ENDPOINT,
    SIDO_NORMALIZE, SPECIAL_FIELD_LABELS_APT, SPECIAL_FIELD_LABELS_RENT,
    URBTY_RENTAL_CODES, LOG_FILE,
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


def _to_int(v) -> int:
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


def _fetch_list(endpoint: str, days: int, label: str) -> List[Dict[str, Any]]:
    """공통 페이지네이션: 최근 N일 이내 모집공고일의 공고 목록 조회."""
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
        logger.info(f"[{label}] {page}페이지 조회 중... (모집공고일 >= {cutoff})")
        data = _get(endpoint, params)
        if not data:
            break

        batch = data.get("data", [])
        items.extend(batch)

        total = data.get("totalCount", 0)
        if not batch or page * per_page >= total:
            break
        page += 1

    logger.info(f"[{label}] 총 {len(items)}건 조회 완료")
    return items


def _fetch_model_rows(endpoint: str, house_manage_no: str, pblanc_no: str) -> List[Dict[str, Any]]:
    params = {
        "page": 1,
        "perPage": 50,
        "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no,
        "cond[PBLANC_NO::EQ]": pblanc_no,
    }
    data = _get(endpoint, params)
    if not data:
        return []
    return data.get("data", [])


# ───────────────────────── APT 분양정보 (매매) ─────────────────────────

def _enrich_apt(notice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    house_no = notice.get("HOUSE_MANAGE_NO", "")
    pblanc_no = notice.get("PBLANC_NO", "")
    name = notice.get("HOUSE_NM", "")
    r_start = notice.get("RCEPT_BGNDE") or ""
    r_end = notice.get("RCEPT_ENDDE") or ""
    notice_date = notice.get("RCRIT_PBLANC_DE") or ""
    win_date = notice.get("PRZWNER_PRESNATN_DE") or r_end

    if not (house_no and pblanc_no and name and r_start and r_end):
        return None

    rows = _fetch_model_rows(APT_MODEL_ENDPOINT, house_no, pblanc_no)
    time.sleep(0.15)

    sizes, prices = [], []
    special_totals = {label: 0 for label in SPECIAL_FIELD_LABELS_APT.values()}
    households = 0

    for row in rows:
        area = _to_float(row.get("SUPLY_AR"))
        if area:
            sizes.append(round(area))
        price = _to_int(row.get("LTTOT_TOP_AMOUNT"))
        if price:
            prices.append(price)
        households += _to_int(row.get("SUPLY_HSHLDCO")) + _to_int(row.get("SPSPLY_HSHLDCO"))
        for field, label in SPECIAL_FIELD_LABELS_APT.items():
            special_totals[label] += _to_int(row.get(field))

    if not sizes:
        sizes = [84]

    sido, gu = _split_address(notice.get("HSSPLY_ADRES", ""))
    special = [label for label, cnt in special_totals.items() if cnt > 0]

    return {
        "id": f"apt_{house_no}_{pblanc_no}",
        "name": name,
        "agency": _agency_from_names(name, notice.get("BSNS_MBY_NM", "")),
        "sido": sido, "gu": gu,
        "addr": notice.get("HSSPLY_ADRES", f"{sido} {gu}".strip()),
        "sizes": sorted(set(sizes)),
        "type": "매매",
        "priceMin": min(prices) if prices else 0,
        "priceMax": max(prices) if prices else 0,
        "deposit": 0, "rent": 0,
        "households": households,
        "special": special,
        "link": notice.get("PBLANC_URL") or notice.get("HMPG_ADRES") or "https://www.applyhome.co.kr/",
        "rStart": r_start, "rEnd": r_end,
        "winDate": win_date, "noticeDate": notice_date,
    }


# ───────────────────── 공공지원 민간임대 (전세) ─────────────────────

def _enrich_rent(notice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    house_no = notice.get("HOUSE_MANAGE_NO", "")
    pblanc_no = notice.get("PBLANC_NO", "")
    name = notice.get("HOUSE_NM", "")
    r_start = notice.get("SUBSCRPT_RCEPT_BGNDE") or ""
    r_end = notice.get("SUBSCRPT_RCEPT_ENDDE") or ""
    notice_date = notice.get("RCRIT_PBLANC_DE") or ""
    win_date = notice.get("PRZWNER_PRESNATN_DE") or r_end

    if not (house_no and pblanc_no and name and r_start and r_end):
        return None

    rows = _fetch_model_rows(RENT_MODEL_ENDPOINT, house_no, pblanc_no)
    time.sleep(0.15)

    sizes, deposits = [], []
    special_totals = {label: 0 for label in SPECIAL_FIELD_LABELS_RENT.values()}
    households = 0

    for row in rows:
        area = _to_float(row.get("EXCLUSE_AR")) or _to_float(row.get("SUPLY_AR"))
        if area:
            sizes.append(round(area))
        amount = _to_int(row.get("SUPLY_AMOUNT"))
        if amount:
            deposits.append(amount)
        households += _to_int(row.get("SUPLY_HSHLDCO"))
        for field, label in SPECIAL_FIELD_LABELS_RENT.items():
            special_totals[label] += _to_int(row.get(field))

    if not sizes:
        sizes = [59]

    sido, gu = _split_address(notice.get("HSSPLY_ADRES", ""))
    special = [label for label, cnt in special_totals.items() if cnt > 0]

    return {
        "id": f"rent_{house_no}_{pblanc_no}",
        "name": name,
        "agency": _agency_from_names(name, notice.get("BSNS_MBY_NM", "")),
        "sido": sido, "gu": gu,
        "addr": notice.get("HSSPLY_ADRES", f"{sido} {gu}".strip()),
        "sizes": sorted(set(sizes)),
        "type": "전세",
        "priceMin": 0, "priceMax": 0,
        "deposit": min(deposits) if deposits else 0,
        "rent": 0,
        "households": households,
        "special": special,
        "link": notice.get("PBLANC_URL") or notice.get("HMPG_ADRES") or "https://www.applyhome.co.kr/",
        "rStart": r_start, "rEnd": r_end,
        "winDate": win_date, "noticeDate": notice_date,
    }


# ─────────────── 오피스텔/도시형/민간임대/생활숙박시설 (매매 또는 월세) ───────────────

def _enrich_urbty(notice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    house_no = notice.get("HOUSE_MANAGE_NO", "")
    pblanc_no = notice.get("PBLANC_NO", "")
    name = notice.get("HOUSE_NM", "")
    r_start = notice.get("SUBSCRPT_RCEPT_BGNDE") or ""
    r_end = notice.get("SUBSCRPT_RCEPT_ENDDE") or ""
    notice_date = notice.get("RCRIT_PBLANC_DE") or ""
    win_date = notice.get("PRZWNER_PRESNATN_DE") or r_end

    if not (house_no and pblanc_no and name and r_start and r_end):
        return None

    house_secd = str(notice.get("SEARCH_HOUSE_SECD", ""))
    is_rental = house_secd in URBTY_RENTAL_CODES  # 0203 민간임대, 0204 생활형숙박시설

    rows = _fetch_model_rows(URBTY_MODEL_ENDPOINT, house_no, pblanc_no)
    time.sleep(0.15)

    sizes, amounts = [], []
    households = 0
    for row in rows:
        area = _to_float(row.get("EXCLUSE_AR"))
        if area:
            sizes.append(round(area))
        amount = _to_int(row.get("SUPLY_AMOUNT"))
        if amount:
            amounts.append(amount)
        households += _to_int(row.get("SUPLY_HSHLDCO"))

    if not sizes:
        sizes = [30]

    sido, gu = _split_address(notice.get("HSSPLY_ADRES", ""))

    # 이 API는 특별공급 세대수 항목을 제공하지 않음
    if is_rental:
        listing_type = "월세"
        deposit_val = min(amounts) if amounts else 0
        price_min = price_max = 0
    else:
        listing_type = "매매"
        deposit_val = 0
        price_min = min(amounts) if amounts else 0
        price_max = max(amounts) if amounts else 0

    return {
        "id": f"urbty_{house_no}_{pblanc_no}",
        "name": name,
        "agency": _agency_from_names(name, notice.get("BSNS_MBY_NM", "")),
        "sido": sido, "gu": gu,
        "addr": notice.get("HSSPLY_ADRES", f"{sido} {gu}".strip()),
        "sizes": sorted(set(sizes)),
        "type": listing_type,
        "priceMin": price_min, "priceMax": price_max,
        "deposit": deposit_val, "rent": 0,
        "households": households,
        "special": [],
        "link": notice.get("PBLANC_URL") or notice.get("HMPG_ADRES") or "https://www.applyhome.co.kr/",
        "rStart": r_start, "rEnd": r_end,
        "winDate": win_date, "noticeDate": notice_date,
    }


def _collect(endpoint: str, label: str, days: int, enrich_fn) -> List[Dict[str, Any]]:
    notices = _fetch_list(endpoint, days, label)
    results = []
    for i, notice in enumerate(notices, 1):
        try:
            item = enrich_fn(notice)
            if item:
                results.append(item)
        except Exception as e:
            logger.error(f"[{label}] 변환 실패 ({notice.get('HOUSE_NM','?')}): {e}")
        if i % 10 == 0:
            logger.info(f"  [{label}] ...{i}/{len(notices)}건 처리 중")
    logger.info(f"[{label}] 최종 변환 완료: {len(results)}건")
    return results


def get_recent_listings(days: int = 14) -> List[Dict[str, Any]]:
    """매매(APT) + 전세(공공지원 민간임대) + 월세(민간임대/생활숙박시설)를 모두 모아 반환."""
    if not API_KEY:
        logger.error("PUBLIC_DATA_API_KEY 환경변수가 설정되지 않았습니다.")
        return []

    all_results: List[Dict[str, Any]] = []

    all_results += _collect(APT_DETAIL_ENDPOINT, "APT/매매", days, _enrich_apt)
    all_results += _collect(RENT_DETAIL_ENDPOINT, "공공지원민간임대/전세", days, _enrich_rent)
    all_results += _collect(URBTY_DETAIL_ENDPOINT, "오피스텔등/매매·월세", days, _enrich_urbty)

    logger.info(f"전체 소스 합산 완료: {len(all_results)}건")
    return all_results
