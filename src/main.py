#!/usr/bin/env python3
"""
청약 공고 자동 수집 시스템
매일 오전 6시에 실행되어 새 청약 공고를 조회하고 archive.json에 기록합니다.
(알림 발송 없이, 데이터 수집·중복 제거만 수행)
"""

import json
import logging
import sys
from pathlib import Path

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from config import LOG_FILE, DATA_DIR, TARGET_REGIONS
from api_client import get_recent_listings
from archiver import get_new_listings
from build_app_data import build as build_app_data

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

LATEST_FILE = DATA_DIR / "latest_new.json"


def main():
    """메인 실행 함수"""
    logger.info("=" * 60)
    logger.info("청약 공고 수집 시작")
    logger.info("=" * 60)

    try:
        # 1. API에서 최근 공고 조회
        logger.info("Step 1: 공공데이터포털에서 공고 조회 중...")
        current_listings = get_recent_listings(days=7)

        if not current_listings:
            logger.warning("조회된 공고가 없습니다.")
            return False

        # 2. 지역별 필터링 (선택사항)
        logger.info("Step 2: 지역 필터링...")
        region_list = list(TARGET_REGIONS.values())
        # 필터링할 경우 주석 해제
        # current_listings = filter_by_region(current_listings, region_list)

        # 3. 아카이브에서 새 공고 찾기 (+ 자동 아카이빙)
        logger.info("Step 3: 새 공고 감지 및 아카이빙...")
        new_listings = get_new_listings(current_listings)

        # 4. 이번 실행에서 새로 찾은 공고를 별도 파일로 저장
        #    (알림은 보내지 않고, 언제든 확인할 수 있도록 기록만 남김)
        with open(LATEST_FILE, "w", encoding="utf-8") as f:
            json.dump(new_listings, f, ensure_ascii=False, indent=2)

        if not new_listings:
            logger.info("새 공고가 없습니다.")
        else:
            logger.info(f"새 공고 {len(new_listings)}개 발견! → {LATEST_FILE}")

        # 5. 웹앱이 읽는 docs/listings.json 갱신
        logger.info("Step 5: 웹앱용 listings.json 생성...")
        build_app_data()

        logger.info("=" * 60)
        logger.info("실행 완료")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
