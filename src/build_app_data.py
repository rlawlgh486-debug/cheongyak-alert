"""
data/archive.json (공공데이터포털 원본 필드) → docs/listings.json (웹앱이 fetch로 읽는 포맷) 변환.

⚠️ 실제 공공데이터포털 API의 정확한 필드명은 로그인 후 Swagger 문서나
   실제 응답을 확인해야 100% 확정할 수 있습니다. 아래 FIELD_MAP은 자주 쓰이는
   필드명을 기준으로 한 최선의 추정치이며, 실제 응답과 다르면 이 파일의
   FIELD_MAP과 to_app_listing() 함수만 수정하면 됩니다. (Claude Code로 실제
   API를 호출해본 뒤 여기를 맞추는 걸 권장합니다.)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from config import ARCHIVE_FILE, DATA_DIR, BASE_DIR, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 웹앱이 있는 폴더 (GitHub Pages가 이 폴더를 서빙함)
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_FILE = DOCS_DIR / "listings.json"


def _agency_from_name(name: str) -> str:
    if "SH" in name or "서울주택" in name:
        return "SH"
    if "LH" in name or "한국토지" in name:
        return "LH"
    return "민간"


def _split_region(region_name: str):
    """'서울 강동구' 같은 문자열을 (시도, 구) 로 분리. 실패하면 (region_name, '')."""
    parts = region_name.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return region_name, ""


def _parse_sizes(supply_area: str):
    """'59.9800,74.8500' 같은 문자열을 [60, 75] 형태로 변환 (반올림)."""
    if not supply_area:
        return [84]
    sizes = []
    for token in str(supply_area).replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            sizes.append(round(float(token)))
        except ValueError:
            continue
    return sorted(set(sizes)) or [84]


def _to_iso_date(raw: str):
    """'20260905' 또는 '2026-09-05' 형태를 'YYYY-MM-DD'로 통일."""
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # 이미 다른 포맷이면 원본 유지 (앱에서 Date 파싱 실패 시 카드에서 빠짐)


def to_app_listing(item: dict, idx: int) -> dict | None:
    """공공데이터포털 정규화 필드 → 웹앱 listings.json 항목."""
    name = item.get("projectName") or item.get("name") or ""
    if not name:
        return None

    sido, gu = _split_region(item.get("regionName", ""))
    price_min = int(item.get("priceMin", 0) or 0)
    price_max = int(item.get("priceMax", 0) or 0)
    special_raw = item.get("specialSupply", "")
    special = [s.strip() for s in str(special_raw).split(",") if s.strip()]

    r_start = _to_iso_date(item.get("receiptStart", ""))
    r_end = _to_iso_date(item.get("receiptEnd", ""))
    notice = _to_iso_date(item.get("announcementDate", "")) or r_start
    if not r_start or not r_end:
        return None  # 접수 기간이 없는 데이터는 앱에서 상태 계산이 안 되므로 제외

    return {
        "id": item.get("noticeNum") or f"N{idx}",
        "name": name,
        "agency": item.get("agency") or _agency_from_name(name),
        "sido": sido,
        "gu": gu,
        "addr": item.get("regionName", sido + " " + gu),
        "sizes": _parse_sizes(item.get("supplyArea", "")),
        "type": "매매" if price_max > 0 else "임대",  # 매매/전세/월세 구분값이 API에 없으면 임시로 이렇게 판단
        "priceMin": price_min,
        "priceMax": price_max,
        "deposit": 0,
        "rent": 0,
        "households": int(item.get("totalSupply", 0) or 0),
        "special": special,
        "link": item.get("link") or "https://www.applyhome.co.kr/",
        "rStart": r_start,
        "rEnd": r_end,
        "winDate": r_end,     # 당첨자 발표일 필드가 별도로 있으면 그 값으로 교체
        "noticeDate": notice,
    }


def build():
    if not ARCHIVE_FILE.exists():
        logger.warning("archive.json이 없습니다. 먼저 수집을 실행하세요.")
        return

    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        archive = json.load(f)

    raw_items = list(archive.get("listings", {}).values())
    app_items = []
    for i, item in enumerate(raw_items):
        converted = to_app_listing(item, i)
        if converted:
            app_items.append(converted)

    DOCS_DIR.mkdir(exist_ok=True)
    output = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(app_items),
        "items": app_items,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"listings.json 생성 완료: {len(app_items)}건 → {OUTPUT_FILE}")


if __name__ == "__main__":
    build()
