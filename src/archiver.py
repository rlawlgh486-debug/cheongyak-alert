import json
import logging
from typing import List, Dict, Set, Tuple
from datetime import datetime
from config import ARCHIVE_FILE, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ArchiveManager:
    """청약 공고 아카이빙 및 중복 체크"""
    
    def __init__(self, archive_path: str = str(ARCHIVE_FILE)):
        self.archive_path = archive_path
        self.archive = self._load_archive()
    
    def _load_archive(self) -> Dict:
        """저장된 아카이브 로드"""
        try:
            if ARCHIVE_FILE.exists():
                with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"아카이브 로드 실패: {e}")
        
        return {
            "listings": {},  # id -> listing data
            "last_update": datetime.now().isoformat(),
            "total_archived": 0,
        }
    
    def _save_archive(self) -> None:
        """아카이브 저장"""
        try:
            self.archive["last_update"] = datetime.now().isoformat()
            with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.archive, f, ensure_ascii=False, indent=2)
            logger.info(f"아카이브 저장 완료 (총 {len(self.archive['listings'])}개)")
        except Exception as e:
            logger.error(f"아카이브 저장 실패: {e}")
    
    def get_archived_notice_nums(self) -> Set[str]:
        """저장된 공고 번호 반환"""
        return set(self.archive.get("listings", {}).keys())
    
    def find_new_listings(self, current_listings: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        새로운 공고와 기존 공고 분리
        
        Returns:
            (new_listings, all_listings_for_update)
        """
        archived = self.get_archived_notice_nums()
        new = []
        
        for listing in current_listings:
            notice_num = listing.get("id")
            if notice_num not in archived:
                new.append(listing)
        
        logger.info(f"새 공고: {len(new)}개, 기존: {len(current_listings) - len(new)}개")
        return new, current_listings
    
    def archive_listings(self, listings: List[Dict]) -> None:
        """공고를 아카이브에 추가"""
        count = 0
        for listing in listings:
            notice_num = listing.get("id")
            if notice_num:
                self.archive["listings"][notice_num] = {
                    **listing,
                    "archived_at": datetime.now().isoformat(),
                }
                count += 1
        
        self.archive["total_archived"] = len(self.archive["listings"])
        self._save_archive()
        logger.info(f"{count}개 공고 아카이빙 완료")
    
    def cleanup_old_listings(self, days: int = 90) -> None:
        """90일 이상 된 공고 정리"""
        from datetime import timedelta, datetime
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        to_delete = [
            num for num, data in self.archive["listings"].items()
            if data.get("archived_at", "") < cutoff
        ]
        
        for num in to_delete:
            del self.archive["listings"][num]
        
        if to_delete:
            self._save_archive()
            logger.info(f"{len(to_delete)}개 오래된 공고 삭제")


def get_new_listings(current_listings: List[Dict]) -> List[Dict]:
    """
    새로운 공고만 반환 (중복 제거)
    """
    manager = ArchiveManager()
    new, _ = manager.find_new_listings(current_listings)
    manager.archive_listings(current_listings)  # 전체 아카이빙
    manager.cleanup_old_listings()
    return new
