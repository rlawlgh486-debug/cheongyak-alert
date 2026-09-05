import os
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ARCHIVE_FILE = DATA_DIR / "archive.json"
DATA_DIR.mkdir(exist_ok=True)

# 공공데이터포털 API
API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")
API_ENDPOINT = "http://apis.data.go.kr/1613000/AptLttotPblancSvc/getAPTLttotPblancList"

# 청약 지역 필터 (행정표준코드)
# 예: 서울 강동구 = 11250
TARGET_REGIONS = {
    "강동구": "11250",
    "강남구": "11680",
    "마포구": "11440",
    "노원구": "11590",
    "은평구": "11530",
    "송파구": "11710",
}

# 로그
LOG_FILE = BASE_DIR / "cheongyak.log"
