import requests
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from config import API_KEY, API_ENDPOINT, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AptLttotClient:
    """공공데이터포털 APT분양정보 조회 API 클라이언트"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = API_ENDPOINT
        
    def fetch_listings(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        모든 APT 분양정보 조회
        """
        listings = []
        page_no = 1
        
        while True:
            try:
                params = {
                    "serviceKey": self.api_key,
                    "numOfRows": page_size,
                    "pageNo": page_no,
                    "type": "json",
                }
                
                logger.info(f"[API] 페이지 {page_no} 조회 중...")
                response = requests.get(self.endpoint, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # 응답 에러 체크
                if "response" not in data:
                    logger.error(f"API 응답 형식 오류: {data}")
                    break
                    
                result = data["response"].get("body", {})
                
                # 데이터 없음
                if result.get("totalCount", 0) == 0:
                    logger.info("조회된 공고가 없습니다.")
                    break
                
                items = result.get("items", [])
                if not items:
                    break
                
                # 공고 리스트에 추가
                if isinstance(items, list):
                    listings.extend(items)
                else:
                    # 단일 항목인 경우
                    listings.append(items)
                
                # 다음 페이지 여부 확인
                total_count = result.get("totalCount", 0)
                if page_no * page_size >= total_count:
                    break
                
                page_no += 1
                
            except requests.RequestException as e:
                logger.error(f"API 호출 실패 (페이지 {page_no}): {e}")
                break
        
        logger.info(f"총 {len(listings)}개 공고 조회 완료")
        return listings
    
    def filter_by_region(self, listings: List[Dict], region_codes: List[str]) -> List[Dict]:
        """
        지역 코드로 필터링
        """
        filtered = []
        for item in listings:
            region_name = item.get("regionName", "")
            # 지역명에 해당 구가 포함되어 있는지 확인
            for region in region_codes:
                if region in region_name:
                    filtered.append(item)
                    break
        
        logger.info(f"지역 필터링: {len(listings)} → {len(filtered)}개")
        return filtered
    
    def normalize_listing(self, raw: Dict) -> Dict:
        """
        API 응답을 앱 포맷으로 정규화
        """
        return {
            "noticeNum": raw.get("noticeNum", ""),
            "projectName": raw.get("projectName", ""),
            "regionName": raw.get("regionName", ""),
            "supplyArea": raw.get("supplyArea", ""),
            "priceMax": int(raw.get("maxPrice", 0)),
            "priceMin": int(raw.get("minPrice", 0)),
            "receiptStart": raw.get("receiptStart", ""),
            "receiptEnd": raw.get("receiptEnd", ""),
            "announcementDate": raw.get("announcementDate", ""),
            "specialSupply": raw.get("specialSupply", ""),
            "agency": self._extract_agency(raw.get("projectName", "")),
            "link": raw.get("link", ""),
        }
    
    def _extract_agency(self, name: str) -> str:
        """프로젝트명에서 공급기관 추출"""
        if "SH" in name or "서울주택" in name:
            return "SH"
        elif "LH" in name or "한국토지" in name:
            return "LH"
        else:
            return "민간"


def get_recent_listings(days: int = 7) -> List[Dict]:
    """
    최근 N일 이내의 공고만 반환
    """
    if not API_KEY:
        logger.error("API_KEY 환경변수가 설정되지 않았습니다.")
        return []
    
    client = AptLttotClient(API_KEY)
    all_listings = client.fetch_listings()
    
    if not all_listings:
        return []
    
    # 공고일 기준으로 필터링 (최근 7일)
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    recent = []
    
    for item in all_listings:
        announce_date = item.get("announcementDate", "")
        if announce_date >= cutoff_date:
            normalized = client.normalize_listing(item)
            recent.append(normalized)
    
    logger.info(f"최근 {days}일 공고: {len(recent)}개")
    return recent
