# 청약모아 — 전국 청약 공고 자동 수집 + 웹앱

매일 오전 6시에 공공데이터포털에서 새 청약 공고를 가져와 `docs/listings.json`을 갱신하고,
`docs/index.html` 웹앱이 그 파일을 읽어 화면에 보여주는 구조입니다.
로그인 없이 브라우저(기기)별로 내 조건·찜 목록이 저장됩니다.

## 폴더 구조

```
cheongyak-auto/
├── docs/                      ← GitHub Pages가 이 폴더를 그대로 서빙
│   ├── index.html             ← 웹앱 (청약모아)
│   ├── listings.json          ← 매일 자동 갱신되는 공고 데이터 (최초엔 없음, 첫 실행 후 생성)
│   ├── manifest.json          ← PWA 설정 (아이폰 홈 화면 추가용)
│   ├── sw.js                  ← 서비스워커 (오프라인 대비 캐싱)
│   └── icons/
│       ├── icon-192.png
│       └── icon-512.png
├── src/
│   ├── main.py                ← 매일 실행되는 메인 스크립트
│   ├── config.py               ← API 키, 지역 설정
│   ├── api_client.py          ← 공공데이터포털 API 호출
│   ├── archiver.py            ← 중복 제거 및 원본 데이터 아카이빙
│   └── build_app_data.py      ← archive.json → docs/listings.json 변환
├── .github/workflows/cheongyak.yml   ← 매일 오전 6시 자동 실행
├── data/                       ← 자동 생성됨 (업로드 불필요)
├── requirements.txt
└── .env.example
```

## 배포 순서

### 1. 공공데이터포털 API 키 발급
data.go.kr 가입 → "청약홈 분양정보 조회 서비스" 검색 → 활용신청 → 승인(1~2시간) → 인증키 복사

### 2. GitHub 저장소 만들고 파일 업로드
1. GitHub에 새 저장소 생성 (Public)
2. 이 폴더 전체(`data/` 제외)를 업로드 — GitHub Desktop 사용 권장
3. **Settings → Secrets and variables → Actions** → `PUBLIC_DATA_API_KEY` 등록

### 3. GitHub Pages 활성화
1. **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, 폴더: **/docs** 선택 → Save
4. 잠시 후 `https://아이디.github.io/저장소명/` 주소가 생성됨

### 4. 첫 실행
**Actions** 탭 → "청약 공고 자동 수집" → **Run workflow**
성공하면 `docs/listings.json`이 생성되어 자동 커밋됩니다.
(이 파일이 아직 없어도 앱은 내장된 예시 데이터로 정상 작동합니다.)

### 5. 접속 확인
2단계에서 만든 Pages 주소로 접속 → 상단에 "○.○○ ○○시 업데이트"가 뜨면 실 데이터 연결 성공.
아직 "예시 데이터"라고 뜨면 4단계가 아직 안 됐거나 실패한 것 — Actions 로그를 확인하세요.

## 아이폰에서 앱처럼 쓰기 (PWA)

네이티브 앱스토어 앱은 아니지만, 아이콘을 눌러 전체화면으로 실행되는 "홈 화면 앱"으로 설치할 수 있습니다.

1. **아이폰 Safari**로 3단계에서 만든 Pages 주소 접속 (다른 브라우저는 안 됨 — 반드시 Safari)
2. 하단 **공유 버튼**(사각형 + 화살표) 탭
3. 아래로 스크롤해서 **"홈 화면에 추가"** 탭
4. 이름 확인 후 **추가**
5. 홈 화면에 "청약모아" 아이콘 생성 → 탭하면 주소창 없이 앱처럼 전체화면으로 실행됨

**주의**: 이렇게 설치한 앱은 Safari가 접속하는 것과 같아서, 인터넷 연결이 필요할 때 최신 `listings.json`을 받아옵니다. 완전 오프라인 상태에서는 마지막으로 불러온 데이터(서비스워커 캐시)나 예시 데이터가 보입니다.

## 매일 자동으로 일어나는 일

```
오전 6시 (KST)
  ↓
GitHub Actions 실행
  ↓
공공데이터포털에서 최근 7일 공고 조회
  ↓
이전에 못 본 새 공고만 구분 (data/archive.json 대조)
  ↓
전체 공고를 docs/listings.json으로 변환 (build_app_data.py)
  ↓
저장소에 자동 커밋 → GitHub Pages에 자동 반영
  ↓
사용자가 앱을 열면 최신 listings.json을 fetch
```

## ⚠️ 실 데이터 연결 시 확인할 것

`src/build_app_data.py`의 필드명(`projectName`, `regionName`, `supplyArea` 등)은
공공데이터포털 API의 실제 응답을 기준으로 최선의 추정치로 작성되어 있습니다.
**실제 응답과 필드명이 다르면 이 파일만 수정하면 됩니다.** Claude Code로 실제
API를 한 번 호출해서 응답을 확인한 뒤 맞추는 걸 권장합니다.

또한 API가 매매/전세/월세를 구분하는 정확한 필드를 제공하는지 확인해서
`to_app_listing()`의 `"type"` 판정 로직도 함께 다듬어주세요 (현재는 분양가
유무로 임시 판정 중).

## 로컬 테스트

```bash
cd cheongyak-auto
export PUBLIC_DATA_API_KEY="your_api_key"
pip install -r requirements.txt
python src/main.py
# docs/listings.json이 생성되면 성공
```

웹앱만 로컬에서 미리보기:
```bash
cd docs
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## 커스터마이징

- **실행 시간**: `.github/workflows/cheongyak.yml`의 `cron: '0 21 * * *'` (UTC 21시 = 한국 오전 6시)
- **지역 필터**: `src/config.py`의 `TARGET_REGIONS`
- **앱 아이콘/이름**: `docs/manifest.json` 및 `docs/icons/` 교체

## 비용

전부 무료입니다 (GitHub Actions 무료 한도, 공공데이터포털 무료 API, GitHub Pages 무료 호스팅).
