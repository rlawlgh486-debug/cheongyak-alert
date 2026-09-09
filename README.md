[README.md](https://github.com/user-attachments/files/32014084/README.md)
# Wishome — 전국 청약 공고 자동 수집 + 웹앱

매일 오전 6시에 청약 공고를 자동으로 모아서 `docs/listings.json`을 갱신하고,
`docs/index.html` 웹앱이 그 파일을 읽어 화면에 보여주는 구조입니다.
로그인 없이 브라우저(기기)별로 내 조건·찜 목록이 저장됩니다.

## 데이터 출처 2곳

1. **공공데이터포털(odcloud) 청약홈 API** — 매매(APT 분양), 전세(공공지원 민간임대),
   월세(오피스텔/도시형/민간임대), 잔여세대(무순위), 임의공급까지 5개 소스
2. **SH(서울주택도시개발공사) 홈페이지 스크래핑** — SH는 청약홈 API에 데이터를
   제공하지 않아서, SH 공식 홈페이지의 "공고 및 공지" 게시판을 직접 읽어와
   제목을 보고 진짜 새 모집공고인지 스스로 판단합니다. 분양가·평형처럼
   확실하지 않은 정보는 지어내지 않고 "SH 홈페이지에서 확인해요"로 안내합니다.

## 폴더 구조

```
cheongyak-auto/
├── docs/                        ← GitHub Pages가 이 폴더를 그대로 서빙
│   ├── index.html               ← 웹앱 (Wishome)
│   ├── listings.json            ← 매일 자동 갱신되는 공고 데이터 (최초엔 없음, 첫 실행 후 생성)
│   ├── manifest.json            ← PWA 설정 (홈 화면 추가용)
│   ├── sw.js                    ← 서비스워커 (오프라인 대비 캐싱)
│   ├── favicon.ico              ← 브라우저 탭 아이콘
│   └── icons/
│       ├── icon-192.png
│       ├── icon-512.png
│       ├── apple-touch-icon.png
│       ├── favicon-32.png
│       └── favicon-16.png
├── src/
│   ├── main.py                  ← 매일 실행되는 메인 스크립트
│   ├── config.py                ← API 엔드포인트, 시/도 명칭 매핑 등 설정
│   ├── api_client.py            ← 공공데이터포털 API 호출 (매매/전세/월세/무순위/임의공급)
│   ├── sh_scraper.py            ← SH 홈페이지 공고 게시판 스크래핑
│   ├── archiver.py              ← 중복 제거 및 원본 데이터 아카이빙
│   └── build_app_data.py        ← archive.json → docs/listings.json 변환
├── .github/workflows/cheongyak.yml   ← 매일 오전 6시 자동 실행
├── data/                         ← 자동 생성됨 (업로드 불필요)
├── requirements.txt
└── .env.example
```

## 배포 순서

### 1. 공공데이터포털 API 키 발급
data.go.kr 가입 → "청약홈 분양정보 조회 서비스" 검색 → 활용신청 → 승인(1~2시간) → 인증키 복사

### 2. GitHub 저장소 만들고 파일 업로드
1. GitHub에 새 저장소 생성 (Public)
2. 이 폴더 전체(`data/` 제외)를 업로드
3. **Settings → Secrets and variables → Actions** → `PUBLIC_DATA_API_KEY` 등록
4. **Settings → Actions → General → Workflow permissions**에서
   **"Read and write permissions"** 선택 → Save (자동 커밋을 위해 필요)

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
Pages 주소로 접속 → 상단에 "○.○○ ○○시 업데이트"처럼 실제 날짜가 뜨면 성공.

## 홈 화면에 앱처럼 추가하기 (PWA)

**아이폰(Safari 전용)**: 사이트 접속 → 공유 버튼 → "홈 화면에 추가"
**안드로이드(Chrome)**: 사이트 접속 → 메뉴(⋮) → "홈 화면에 추가" 또는 자동으로 뜨는 배너 사용

## 앱 기능 요약

- 전국 공고를 시/도 → 구/동 순으로 필터링
- SH·LH 같은 공공기관 공고가 항상 먼저 보이도록 정렬 + 기관별(SH/LH/민간) 필터
- 매매/전세/월세 유형 구분, 접수중만 보기, 마감된 공고 자동 숨김
- 청약가점(무주택기간·부양가족·통장 납입) 입력 → 공고별 적합도 자동 계산
- 찜하기 및 여러 개 선택삭제

## ⚠️ 알아두어야 할 한계

1. **API 필드명**: `src/api_client.py`의 필드명은 공공데이터포털 Swagger 문서 기준으로
   작성했지만, 실제 응답과 다르면 이 파일만 수정하면 됩니다.
2. **SH 스크래핑**: `src/sh_scraper.py`는 SH 홈페이지 구조가 바뀌면 깨질 수 있습니다.
   로그에 "목록에서 행을 하나도 못 찾았습니다"가 뜨면 사이트 구조를 다시 확인해야 합니다.
   또한 SH가 올리는 행복주택·청년안심주택 등은 제목만으로 정확한 분양가·평형을
   알 수 없어서, 앱에서 "SH 홈페이지에서 확인해요"로 안내합니다.
3. **다른 지방공사(iH, GH 등)**: 아직 연결 안 됨. 필요하면 SH 스크래퍼와 비슷한
   방식으로 추가할 수 있습니다.

## 로컬 테스트

```bash
cd cheongyak-auto
export PUBLIC_DATA_API_KEY="your_api_key"
pip install -r requirements.txt
python src/main.py
```

웹앱만 로컬에서 미리보기:
```bash
cd docs
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## 커스터마이징

- **실행 시간**: `.github/workflows/cheongyak.yml`의 `cron: '0 21 * * *'` (UTC 21시 = 한국 오전 6시)
- **앱 이름/아이콘**: `docs/manifest.json`과 `docs/icons/` 교체, `docs/index.html`의 `<title>` 및 상단 `<h1>Wishome</h1>` 수정

## 비용

전부 무료입니다 (GitHub Actions 무료 한도, 공공데이터포털 무료 API, GitHub Pages 무료 호스팅).
