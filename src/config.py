import os
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ARCHIVE_FILE = DATA_DIR / "archive.json"
DATA_DIR.mkdir(exist_ok=True)

# 공공데이터포털(odcloud) API — 청약홈 분양정보 조회 서비스
# Swagger: https://infuser.odcloud.kr/api/stages/37000/api-docs
API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")

API_HOST = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1"

# APT 분양정보 (=매매) — 공고 목록 / 주택형별 상세(분양가·평형·특별공급)
APT_DETAIL_ENDPOINT = f"{API_HOST}/getAPTLttotPblancDetail"
APT_MODEL_ENDPOINT = f"{API_HOST}/getAPTLttotPblancMdl"

# 오피스텔/도시형/민간임대/생활숙박시설 — 공고 목록 / 주택형별 상세
URBTY_DETAIL_ENDPOINT = f"{API_HOST}/getUrbtyOfctlLttotPblancDetail"
URBTY_MODEL_ENDPOINT = f"{API_HOST}/getUrbtyOfctlLttotPblancMdl"

# 공공지원 민간임대 (=전세) — 공고 목록 / 주택형별 상세
RENT_DETAIL_ENDPOINT = f"{API_HOST}/getPblPvtRentLttotPblancDetail"
RENT_MODEL_ENDPOINT = f"{API_HOST}/getPblPvtRentLttotPblancMdl"

# 시/도 전체 명칭 -> 앱에서 쓰는 축약 명칭
SIDO_NORMALIZE = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "제주도": "제주",
}

# 특별공급 세대수 필드 -> 표시 라벨 (APT 분양)
SPECIAL_FIELD_LABELS_APT = {
    "NWWDS_HSHLDCO": "신혼부부",
    "MNYCH_HSHLDCO": "다자녀가구",
    "LFE_FRST_HSHLDCO": "생애최초",
    "OLD_PARNTS_SUPORT_HSHLDCO": "노부모부양",
    "INSTT_RECOMEND_HSHLDCO": "기관추천",
}

# 특별공급 세대수 필드 -> 표시 라벨 (공공지원 민간임대 = 전세)
SPECIAL_FIELD_LABELS_RENT = {
    "SPSPLY_YGMN_HSHLDCO": "청년",
    "SPSPLY_NEW_MRRG_HSHLDCO": "신혼부부",
    "SPSPLY_AGED_HSHLDCO": "고령자",
}

# 오피스텔/도시형/민간임대/생활숙박시설 주택구분코드
# 0201:도시형생활주택(매매), 0202:오피스텔(매매), 0203:민간임대(월세), 0204:생활형숙박시설(매매)
URBTY_RENTAL_CODES = {"0203", "0204"}

# 로그
LOG_FILE = BASE_DIR / "cheongyak.log"
