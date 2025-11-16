# 📊 예측 시장 (Prediction Market) 시스템 사용 가이드

Polymarket 스타일의 예측 시장 플랫폼 - AI 헤지펀드 시스템에 통합

## 🎯 시스템 개요

### 핵심 기능
1. **예측 주제 생성**: 주식, 경제, 문화, 기술 등 다양한 주제에 대한 예측
2. **커뮤니티 예측**: 사용자들이 확률 기반으로 예측 제출
3. **AI 에이전트 참여**: 15개 AI 투자 에이전트의 자동 예측
4. **실시간 컨센서스**: 커뮤니티 평균 예측 및 추이 분석
5. **결과 검증**: 실제 결과 확정 및 정확도 계산 (Brier Score)
6. **투자 시그널 생성**: 예측 데이터를 투자 의사결정에 활용
7. **리더보드**: 예측자별 정확도 순위

## 📦 시스템 구성

### 1. 데이터베이스 스키마
```
supabase_prediction_market.sql
- prediction_topics: 예측 주제 관리
- user_predictions: 사용자 및 AI 예측
- prediction_accuracy: 예측 정확도 추적
- predictor_performance: 예측자 성과 요약
- community_consensus: 커뮤니티 컨센서스 (VIEW)
- investment_signals: 투자 시그널 생성 (VIEW)
```

### 2. 백엔드 API
```
src/tools/prediction_market.py
- PredictionMarket 클래스: 모든 예측 시장 로직
- Pydantic 모델: 타입 안전성 보장

api_prediction_market.py
- FastAPI 라우터: /api/prediction/* 엔드포인트
- 20+ API 엔드포인트 제공
```

### 3. 프론트엔드 UI
```
web/prediction_market.html
- Polymarket 스타일 다크 테마 UI
- Chart.js 기반 실시간 시각화
- 완전 반응형 디자인
```

## 🚀 시작하기

### 1단계: 데이터베이스 설정

Supabase에 스키마를 적용합니다:

```bash
# Supabase CLI 사용
supabase db push < supabase_prediction_market.sql

# 또는 Supabase 대시보드에서 SQL Editor를 사용
# 파일 내용을 복사해서 실행
```

### 2단계: 웹 서버 실행

```bash
# 가상환경 활성화
source ai-hedge-env/bin/activate

# 웹 서버 실행 (포트 8888)
python simple_web_api.py
```

### 3단계: 웹 인터페이스 접속

브라우저에서 다음 주소로 접속:

```
http://192.168.1.3:8888/prediction-market
또는
http://localhost:8888/prediction-market
```

## 📖 사용 방법

### 예측 주제 만들기

API를 통해 새로운 예측 주제를 생성할 수 있습니다:

```bash
curl -X POST http://192.168.1.3:8888/api/prediction/topics \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AAPL이 2025년 Q1 실적 발표에서 매출 예상치를 상회할까?",
    "description": "Apple의 2025년 1분기 실적 발표가 3월 예정입니다.",
    "category": "stock",
    "question_type": "binary",
    "deadline": "2025-03-31T23:59:59Z",
    "tags": ["AAPL", "earnings", "tech"],
    "related_tickers": ["AAPL"],
    "data_source": "yahoo_finance"
  }'
```

### 예측 제출하기

웹 UI에서:
1. 주제 카드 클릭
2. 예측 확률 슬라이더 조정 (0-100%)
3. 신뢰도 선택 (낮음/보통/높음)
4. 근거 입력 (선택사항)
5. "예측 제출" 버튼 클릭

또는 API를 통해:

```bash
curl -X POST http://192.168.1.3:8888/api/prediction/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": 1,
    "prediction_value": 65.0,
    "confidence_level": "high",
    "reasoning": "실적 가이던스가 긍정적이고, iPhone 판매가 예상보다 강함"
  }'
```

### AI 에이전트 자동 예측

특정 주제에 대해 모든 AI 에이전트의 예측을 자동 생성:

```bash
curl -X POST http://192.168.1.3:8888/api/prediction/ai-predict/1
```

15개 AI 에이전트 (Warren Buffett, Peter Lynch, Cathie Wood 등)가 자동으로 예측을 생성합니다.

### 결과 확정 및 정확도 계산

예측 주제가 마감되면 관리자가 실제 결과를 확정합니다:

```bash
# 주제 마감
curl -X POST http://192.168.1.3:8888/api/prediction/topics/1/close

# 결과 확정 (yes/no)
curl -X POST http://192.168.1.3:8888/api/prediction/topics/1/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "actual_outcome": "yes",
    "resolution_notes": "AAPL Q1 매출 $950억으로 애널리스트 컨센서스 $925억 상회"
  }'
```

결과 확정 시 자동으로:
- 모든 예측의 Brier Score 계산
- 정확도 퍼센티지 산출
- 예측자별 성과 업데이트
- 리더보드 순위 갱신

## 🎯 주요 API 엔드포인트

### 예측 주제 관리
```
GET    /api/prediction/topics              # 주제 목록
GET    /api/prediction/topics/{id}         # 주제 상세
POST   /api/prediction/topics              # 주제 생성
POST   /api/prediction/topics/{id}/close   # 주제 마감
POST   /api/prediction/topics/{id}/resolve # 결과 확정
```

### 예측 제출
```
POST   /api/prediction/predictions                # 예측 제출
GET    /api/prediction/predictions/topic/{id}     # 주제별 예측 조회
GET    /api/prediction/predictions/user/{id}      # 사용자별 예측 조회
```

### 컨센서스 및 통계
```
GET    /api/prediction/consensus              # 커뮤니티 컨센서스
GET    /api/prediction/consensus/ai           # AI 에이전트 컨센서스
GET    /api/prediction/signals                # 투자 시그널
GET    /api/prediction/leaderboard            # 리더보드
GET    /api/prediction/trending               # 인기 주제
GET    /api/prediction/market-sentiment/{cat} # 카테고리별 감성
```

### 대시보드
```
GET    /api/prediction/dashboard              # 통합 대시보드 데이터
```

## 📊 정확도 메트릭

### Brier Score
예측 정확도를 측정하는 표준 지표:
```
Brier Score = (예측 확률/100 - 실제 결과)^2

- 0 = 완벽한 예측
- 1 = 최악의 예측
- < 0.1 = 매우 정확
- < 0.25 = 정확
- < 0.5 = 보통
- > 0.75 = 부정확
```

### 정확도 퍼센티지
```
정확도 = 100 - |예측 확률 - 실제 결과|
```

## 🔄 AI 에이전트 통합 (향후 작업)

현재 API는 AI 에이전트 통합을 위한 인터페이스를 제공하지만, 실제 AI 에이전트와의 연동은 다음 단계에서 구현할 예정입니다:

### 통합 계획
1. **에이전트별 분석 로직**
   - Warren Buffett: 펀더멘털 분석 기반 예측
   - Peter Lynch: 성장주 관점 예측
   - Cathie Wood: 혁신 기술 중심 예측
   - 등 15개 에이전트

2. **자동 예측 생성**
   - 예측 주제 생성 시 자동으로 AI 에이전트 호출
   - 각 에이전트의 투자 철학 반영
   - 근거 및 신뢰도 자동 생성

3. **성과 추적**
   - AI 에이전트별 예측 정확도 추적
   - 인간 vs AI 성과 비교
   - 에이전트별 강점 분야 분석

## 🎨 UI 사용 팁

### 탭별 기능
1. **트렌딩**: 가장 인기 있는 예측 주제 (참여자 수 기준)
2. **모든 주제**: 모든 열린 예측 주제
3. **리더보드**: 예측 정확도 순위
4. **투자 시그널**: 예측 시장 데이터 기반 매수/매도 시그널

### 색상 코드
- **보라색**: 커뮤니티 컨센서스
- **초록색**: 강세 예측 (>65%)
- **빨간색**: 약세 예측 (<35%)
- **파란색**: AI 에이전트

## 🧪 테스트 방법

### 수동 테스트

1. 예측 주제 생성 후 웹 UI 확인
2. 여러 예측 제출하고 컨센서스 확인
3. 주제 마감 및 결과 확정
4. 리더보드 업데이트 확인

### E2E 테스트 (향후 작업)

```bash
# Playwright 기반 E2E 테스트 작성 예정
python test_prediction_market_e2e.py
```

## 🔧 트러블슈팅

### 데이터베이스 연결 오류
```
Error: Could not connect to Supabase
해결: .env 파일의 SUPABASE_URL 및 SUPABASE_KEY 확인
```

### API 엔드포인트 404
```
Error: 404 Not Found /api/prediction/topics
해결: simple_web_api.py에 라우터가 제대로 통합되었는지 확인
```

### 웹 페이지 로드 실패
```
Error: 500 Internal Server Error
해결: web/prediction_market.html 파일 존재 확인
```

## 📈 향후 계획

### Phase 1 (완료)
- ✅ 데이터베이스 스키마 설계
- ✅ FastAPI 백엔드 구현
- ✅ 웹 프론트엔드 UI 구현
- ✅ 기본 API 엔드포인트 완성

### Phase 2 (진행 중)
- ⏳ AI 에이전트 통합
- ⏳ E2E 테스트 작성
- ⏳ 샘플 데이터 생성

### Phase 3 (계획)
- ⬜ 실시간 WebSocket 업데이트
- ⬜ 예측 차트 및 시각화 개선
- ⬜ 모바일 반응형 최적화
- ⬜ 알림 시스템 (이메일, Slack)

### Phase 4 (계획)
- ⬜ 포인트 시스템 및 게임화
- ⬜ 소셜 기능 (댓글, 공유)
- ⬜ 고급 분석 대시보드
- ⬜ API 문서 자동 생성 (Swagger 개선)

## 📚 참고 자료

- **Polymarket**: https://polymarket.com (예측 시장 플랫폼)
- **Brier Score**: https://en.wikipedia.org/wiki/Brier_score
- **Supabase 문서**: https://supabase.com/docs
- **FastAPI 문서**: https://fastapi.tiangolo.com

## 🤝 기여

이 시스템을 개선하고 싶으시다면:
1. 새로운 AI 에이전트 추가
2. 예측 정확도 메트릭 개선
3. UI/UX 개선
4. 버그 수정 및 성능 최적화

## 📞 문의

시스템 관련 문의사항이나 버그 리포트는 GitHub Issues에 등록해주세요.

---

**마지막 업데이트**: 2025-10-24
**버전**: 1.0.0
**상태**: MVP 완성, AI 에이전트 통합 진행 중
