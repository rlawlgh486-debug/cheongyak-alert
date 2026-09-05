"""
data/archive.json (이미 웹앱 스키마로 저장된 공고들) → docs/listings.json 로 감싸서 출력.
api_client.py의 enrich_with_model()이 저장 시점에 이미 앱이 쓰는 필드 구조로
변환해두기 때문에, 여기서는 추가 변환 없이 래퍼만 씌운다.
"""

import json
import logging
from datetime import datetime, timezone
from config import ARCHIVE_FILE, BASE_DIR, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DOCS_DIR = BASE_DIR / "docs"
OUTPUT_FILE = DOCS_DIR / "listings.json"


def build():
    if not ARCHIVE_FILE.exists():
        logger.warning("archive.json이 없습니다. 먼저 수집을 실행하세요.")
        return

    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        archive = json.load(f)

    items = list(archive.get("listings", {}).values())
    # archived_at 등 내부 메타 필드는 웹앱에 불필요하므로 필요한 필드만 추림
    keys = [
        "id", "name", "agency", "sido", "gu", "addr", "sizes", "type",
        "priceMin", "priceMax", "deposit", "rent", "households",
        "special", "link", "rStart", "rEnd", "winDate", "noticeDate",
    ]
    clean_items = [{k: item.get(k) for k in keys} for item in items]

    DOCS_DIR.mkdir(exist_ok=True)
    output = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(clean_items),
        "items": clean_items,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"listings.json 생성 완료: {len(clean_items)}건 → {OUTPUT_FILE}")


if __name__ == "__main__":
    build()
