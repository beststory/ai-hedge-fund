# AI 투자 지능 시스템 사용 가이드

## 🎯 시스템 개요

AI 투자 지능 시스템은 1,877개의 블로그 포스트 분석을 기반으로 투자 시나리오를 생성하고, 포트폴리오 최적화 및 성과 추적을 자동화하는 시스템입니다.

## 🚀 빠른 시작

### 1. 웹 접속

**메인 페이지**: http://192.168.1.3:8888

메인 페이지 헤더에서 **"🧠 AI 지능 시스템"** 버튼 클릭

또는 직접 접속: http://192.168.1.3:8888/intelligence.html

### 2. 로그인

- 사용자명: `admin`
- 비밀번호: `hedge2024!`

### 3. 시나리오 생성

1. "투자 시나리오" 탭에서 **"시나리오 생성 (3개)"** 버튼 클릭
2. AI가 현재 경제 상황을 분석하여 3개의 시나리오 생성:
   - 낙관적 시나리오 (높은 수익률, 높은 리스크)
   - 중립적 시나리오 (균형잡힌 수익률, 보통 리스크)
   - 비관적 시나리오 (낮은 수익률, 낮은 리스크)

### 4. 시나리오 선택 및 리밸런싱

1. 생성된 시나리오 중 하나를 클릭하여 선택
2. "포트폴리오" 탭으로 자동 전환
3. 리밸런싱 계획 확인:
   - Buy/Sell/Hold 액션
   - 예상 거래 비용
   - 자산 배분 변화

## 📊 주요 기능

### 1. 시나리오 생성 (Scenario Generation)

**경제 지표 분석**:
- GDP 성장률
- 인플레이션율
- 실업률
- 기준 금리
- PMI 지수

**블로그 인사이트 활용**:
- 1,877개 블로그 포스트에서 시장 감성 분석
- RAG (Retrieval-Augmented Generation) 기반 인사이트 추출
- 섹터별, 키워드별 트렌드 파악

**시나리오 구성**:
- 시나리오 이름 및 설명
- 발생 확률 (%)
- 예상 수익률 (%)
- 리스크 수준 (낮음/보통/높음)
- 자산 배분 제안 (주식, 채권, ETF, 현금 등)

### 2. 포트폴리오 최적화 (Portfolio Optimization)

**현재 포트폴리오 분석**:
- 보유 종목 및 평가액
- 현재 자산 배분 비율
- 손익률 (PnL)

**리밸런싱 계획**:
- 목표 자산 배분 계산
- Buy/Sell/Hold 액션 생성
- 예상 거래 비용 계산
- 종목별 변경 이유 제공

**자동 가격 조회**:
- Yahoo Finance 실시간 가격
- 미국, 일본, 중국, 홍콩 등 글로벌 시장 지원

### 3. 성과 분석 (Performance Analysis)

**성과 지표 계산**:
- 총 수익률 (Total Return)
- Sharpe Ratio (샤프 비율)
- 최대 낙폭 (Max Drawdown)
- 변동성 (Volatility)
- 승률 (Win Rate)

**AI 자동 학습**:
- 예측 vs 실제 성과 비교
- 성공/실패 키워드 가중치 조정
- 학습 인사이트 추출

### 4. AI 학습 (AI Learning)

**모델 가중치 시각화**:
- 키워드별 가중치 (0.0 ~ 1.0)
- 성공/실패 횟수
- 신뢰도 점수

**지속적 개선**:
- 실제 성과를 기반으로 AI 모델 자동 업데이트
- 정확도 향상 추적

## 🏗️ 시스템 아키텍처

### 백엔드 모듈

```
src/intelligence/
├── scenario_generator.py       # 시나리오 생성 엔진
├── portfolio_optimizer.py      # 포트폴리오 최적화
├── portfolio_tracker.py        # 포트폴리오 추적
├── performance_analyzer.py     # 성과 분석 및 AI 학습
└── blog_backtester.py          # 블로그 백테스팅
```

### API 엔드포인트

```
POST   /api/intelligence/scenarios/generate       # 시나리오 생성
GET    /api/intelligence/scenarios/list           # 시나리오 목록
GET    /api/intelligence/scenarios/{id}           # 시나리오 상세
POST   /api/intelligence/portfolio/rebalance      # 리밸런싱 계획
GET    /api/intelligence/portfolio/current        # 현재 포트폴리오
POST   /api/intelligence/performance/analyze      # 성과 분석
GET    /api/intelligence/learning/weights         # AI 가중치 조회
```

### 데이터베이스 스키마

**핵심 테이블** (Supabase):
- `investment_scenarios` - AI 생성 시나리오
- `user_portfolios` - 사용자 포트폴리오 스냅샷
- `portfolio_transactions` - 거래 내역
- `scenario_performance` - 시나리오 성과 추적
- `ai_model_weights` - AI 모델 학습 가중치
- `asset_allocation_history` - 자산 배분 히스토리
- `blog_backtest_results` - 블로그 백테스팅 결과

## 🔧 기술 스택

- **백엔드**: Python 3.12, FastAPI
- **AI**: Ollama (nomic-embed-text), OpenAI (선택사항)
- **데이터베이스**: Supabase (PostgreSQL + pgvector)
- **실시간 데이터**: Yahoo Finance API
- **프론트엔드**: HTML/CSS/JavaScript

## 📈 사용 시나리오

### 시나리오 1: 정기적 포트폴리오 리밸런싱

1. **매월 1일**: 새로운 시나리오 생성
2. **경제 상황 평가**: AI가 자동으로 경제 지표 분석
3. **시나리오 선택**: 본인의 투자 성향에 맞는 시나리오 선택
4. **리밸런싱 실행**: 제안된 Buy/Sell 액션 검토 후 실행
5. **성과 추적**: 3개월 후 실제 성과 vs 예상 성과 비교

### 시나리오 2: 경제 위기 대응

1. **위기 감지**: 경제 지표 급변 시 시나리오 재생성
2. **비관적 시나리오**: 방어적 포지션 시나리오 선택
3. **신속 리밸런싱**: 채권/현금 비중 증가
4. **리스크 관리**: 최대 낙폭 모니터링

### 시나리오 3: 성장 기회 포착

1. **긍정적 신호**: 블로그 인사이트에서 특정 섹터 강세 감지
2. **낙관적 시나리오**: 성장주 중심 시나리오 선택
3. **공격적 배분**: 기술주/AI 관련주 비중 증가
4. **성과 극대화**: Sharpe Ratio 최적화

## 🧪 테스트 방법

### E2E 테스트 실행

```bash
source ai-hedge-env/bin/activate
python test_intelligence_system.py
```

**테스트 항목**:
1. ✅ 시나리오 생성 (경제 지표 수집, AI 시나리오 생성)
2. ✅ 포트폴리오 최적화 (리밸런싱 계획 생성)
3. ✅ 포트폴리오 추적 (현재 포지션 조회)
4. ✅ 성과 분석 (Sharpe Ratio, MDD 계산)

### API 테스트

```bash
# 시나리오 생성
curl -X POST http://192.168.1.3:8888/api/intelligence/scenarios/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"num_scenarios": 3}'

# 시나리오 목록 조회
curl http://192.168.1.3:8888/api/intelligence/scenarios/list \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## ⚠️ 주의사항

### Supabase 테이블 생성

현재 Supabase 테이블은 **수동 생성**이 필요합니다:

1. Supabase Dashboard (https://supabase.com) 접속
2. SQL Editor 열기
3. `supabase_intelligence_system.sql` 파일 내용 복사
4. 실행

또는 psql CLI 사용:
```bash
psql -h YOUR_SUPABASE_HOST -U postgres -d postgres -f supabase_intelligence_system.sql
```

### 데이터 보안

- **Row-Level Security (RLS)**: 사용자는 본인 데이터만 접근 가능
- **JWT 인증**: 모든 API 호출은 JWT 토큰 필요
- **Service Role Key**: `.env`에서 안전하게 관리

### 성능 최적화

- **캐싱**: 경제 지표는 1시간 캐시
- **배치 처리**: 블로그 인사이트 검색은 병렬 처리
- **인덱스**: 주요 쿼리에 대한 데이터베이스 인덱스 설정

## 🔮 향후 개선 계획

1. **실시간 알림**: 시나리오 발생 확률 변화 시 알림
2. **자동 거래**: 승인된 시나리오에 대해 자동 리밸런싱
3. **백테스팅 UI**: 과거 시나리오 성과 시각화
4. **멀티 사용자**: 사용자별 독립적인 포트폴리오 관리
5. **모바일 앱**: 모바일 대시보드 개발

## 📚 추가 자료

- **PRD 문서**: `INVESTMENT_INTELLIGENCE_SYSTEM_PRD.md`
- **Supabase 스키마**: `supabase_intelligence_system.sql`
- **백엔드 코드**: `src/intelligence/`
- **웹 UI**: `web/intelligence.html`
- **API 서버**: `simple_web_api.py`

## 💬 지원

문제 발생 시:
1. `/tmp/web_server.log` 로그 확인
2. Supabase 연결 상태 확인
3. Ollama 서버 상태 확인 (`curl http://localhost:11434`)

---

**마지막 업데이트**: 2025-11-16
**버전**: 1.0.0
