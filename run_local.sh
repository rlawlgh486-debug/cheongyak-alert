#!/bin/bash

# 청약 공고 자동 수집 시스템 로컬 테스트 스크립트

set -e

echo "================================"
echo "청약 공고 수집 로컬 테스트"
echo "================================"

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "   .env.example을 복사해서 .env로 만들고 API 키를 입력해주세요:"
    echo ""
    echo "   cp .env.example .env"
    echo ""
    exit 1
fi

# 환경변수 로드
export $(cat .env | grep -v '#' | xargs)

# Python 버전 확인
echo "✓ Python 버전 확인 중..."
python3 --version

# 의존성 설치
echo "✓ 의존성 설치 중..."
pip install -q -r requirements.txt

# 실행
echo "✓ 실행 중..."
python3 src/main.py

echo ""
echo "================================"
echo "✅ 실행 완료"
echo "================================"
echo ""
echo "📝 로그 보기:"
echo "   tail -f cheongyak.log"
