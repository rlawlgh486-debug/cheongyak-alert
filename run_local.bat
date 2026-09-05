@echo off
REM 청약 공고 자동 수집 시스템 로컬 테스트 스크립트 (Windows)

setlocal enabledelayedexpansion

echo ================================
echo 청약 공고 수집 로컬 테스트
echo ================================
echo.

REM .env 파일 확인
if not exist ".env" (
    echo 경고: .env 파일이 없습니다.
    echo.
    echo .env.example을 복사해서 .env로 만들고 API 키를 입력해주세요:
    echo.
    echo     copy .env.example .env
    echo.
    pause
    exit /b 1
)

REM 환경변수 로드
for /f "delims=" %%a in ('type .env ^| findstr /v "^#"') do (
    set "%%a"
)

REM Python 버전 확인
echo 체크: Python 버전 확인 중...
python --version
if errorlevel 1 (
    echo 에러: Python을 찾을 수 없습니다.
    echo Python 3.9 이상 설치 후 다시 시도해주세요.
    pause
    exit /b 1
)

REM 의존성 설치
echo 체크: 의존성 설치 중...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo 에러: 의존성 설치 실패
    pause
    exit /b 1
)

REM 실행
echo 체크: 실행 중...
python src/main.py
if errorlevel 1 (
    echo 에러: 실행 중 오류 발생
    pause
    exit /b 1
)

echo.
echo ================================
echo 완료: 실행 성공
echo ================================
echo.
echo 팁: 로그 보기
echo     type cheongyak.log
echo.
pause
