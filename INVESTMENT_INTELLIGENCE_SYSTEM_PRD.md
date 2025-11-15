# AI 기반 지능형 투자 분석 시스템 PRD

## 📋 개요

### 목적
매일 블로그와 뉴스 분석을 기반으로 과거 데이터를 백테스팅하여 다양한 시나리오를 생성하고, 사용자가 선택한 시나리오에 따라 최적의 자산 배분을 제안하며, 실제 투자 결과를 추적하여 지속적으로 학습하는 지능형 투자 분석 시스템

### 핵심 가치
1. **데이터 기반 의사결정**: 매일 블로그 1,877개 글 + 실시간 뉴스 분석
2. **과거 검증**: 블로그 인사이트 백테스팅으로 신뢰도 확보
3. **다중 시나리오**: 다양한 경제 상황별 대응 전략
4. **개인화**: 사용자 투자 성향 및 포트폴리오 맞춤
5. **지속 학습**: 투자 결과 피드백을 통한 AI 모델 개선

---

## 🏗️ 시스템 아키텍처

### 1. 데이터 레이어
```
데이터 소스:
├── 매일 블로그 (1,877개 글)
│   ├── data/blog_raw_all.json
│   ├── data/investment_insights_all.json
│   └── Supabase pgvector (RAG 검색)
├── 뉴스 피드
│   ├── RSS 기반 실시간 수집
│   ├── 감성 분석
│   └── 지정학적 리스크 분석
├── 시장 데이터
│   ├── Yahoo Finance (미국, 일본, 중국, 한국)
│   ├── 경제 지표 (GDP, CPI, 금리, 실업률)
│   └── 환율 데이터
└── 사용자 데이터
    ├── 포트폴리오 현황
    ├── 투자 성향
    └── 과거 투자 결과
```

### 2. AI 엔진 레이어
```
AI 분석 엔진:
├── 블로그 백테스팅 엔진
│   ├── 시점별 블로그 인사이트 추출
│   ├── 해당 시점 이후 실제 시장 변화 분석
│   └── 인사이트-결과 상관관계 학습
├── 시나리오 생성 엔진
│   ├── 경제 상황 패턴 인식
│   ├── 다중 시나리오 생성 (낙관/중립/비관)
│   └── 각 시나리오별 확률 계산
├── 자산 배분 최적화 엔진
│   ├── 선택된 시나리오 기반 배분
│   ├── 리스크 허용도 반영
│   └── 글로벌 분산 투자 (미국/일본/중국/한국/ETF/원자재)
└── 성과 분석 및 학습 엔진
    ├── 실제 vs 예측 비교
    ├── 성공/실패 패턴 학습
    └── 모델 가중치 자동 조정
```

### 3. 애플리케이션 레이어
```
웹 인터페이스:
├── 대시보드
│   ├── 현재 시장 상황 요약
│   ├── AI 생성 시나리오 목록
│   └── 추천 자산 배분
├── 백테스팅 결과 시각화
│   ├── 블로그 인사이트별 성공률
│   ├── 시나리오별 과거 성과
│   └── 시계열 차트
├── 시나리오 선택 인터페이스
│   ├── 3-5개 시나리오 제시
│   ├── 각 시나리오 상세 설명
│   └── 확률 및 리스크 표시
├── 포트폴리오 관리
│   ├── 현재 보유 자산 입력
│   ├── 리밸런싱 제안
│   └── 실시간 수익률 추적
└── 성과 분석
    ├── 과거 추천 vs 실제 결과
    ├── 성공률 통계
    └── 개선 제안
```

---

## 🎯 핵심 기능

### Phase 1: 블로그 백테스팅 시스템 (우선순위: 최상)

#### 1.1 시점별 데이터 분할
```python
# data/blog_raw_all.json (1,877개 글)을 시점별로 분할
시점 1 (2024-01): 블로그 글 100개
  └─> 2024-02~현재까지 시장 변화 분석
시점 2 (2024-02): 블로그 글 120개
  └─> 2024-03~현재까지 시장 변화 분석
...
시점 N (2025-10): 최신 블로그 글
  └─> 아직 검증 안 됨 (미래 데이터)
```

#### 1.2 인사이트-결과 상관관계 분석
```
블로그에서 "삼성전자 반도체 호황 예상" (2024-01-15)
  ├─> 실제 삼성전자 주가: 2024-01-15 ~ 2024-04-15 (+15%)
  ├─> 상관계수: 0.87
  └─> 신뢰도: 높음

블로그에서 "금리 인상 우려" (2024-03-10)
  ├─> 실제 금리: 2024-03-10 ~ 2024-06-10 (+0.25%)
  ├─> 주식 시장: -5%
  └─> 신뢰도: 중간
```

#### 1.3 백테스팅 결과 Supabase 저장
```sql
CREATE TABLE blog_backtest_results (
    id SERIAL PRIMARY KEY,
    blog_id INTEGER,
    insight_text TEXT,
    insight_date TIMESTAMP,
    prediction_topic VARCHAR(100),  -- 예: "삼성전자", "금리", "반도체"
    prediction_direction VARCHAR(20),  -- "상승", "하락", "중립"
    actual_outcome JSONB,  -- 실제 결과 데이터
    correlation_score FLOAT,  -- -1.0 ~ 1.0
    confidence_level VARCHAR(20),  -- "높음", "중간", "낮음"
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Phase 2: 다중 시나리오 생성 엔진

#### 2.1 현재 경제 상황 분석
```python
현재 상황 스냅샷:
├── 매크로 지표
│   ├── GDP 성장률: 2.5%
│   ├── 인플레이션: 3.2%
│   ├── 실업률: 3.8%
│   └── 기준 금리: 5.25%
├── 시장 센티먼트
│   ├── VIX 지수: 15.2 (낮음 = 안정적)
│   ├── 뉴스 감성: 중립 (0.05)
│   └── 블로그 분위기: 긍정적 (0.15)
└── 지정학적 리스크
    ├── 미중 무역 긴장: 보통
    ├── 중동 정세: 안정적
    └── 에너지 가격: 안정적
```

#### 2.2 시나리오 생성 알고리즘
```python
def generate_scenarios(current_situation: Dict) -> List[Scenario]:
    """
    3-5개의 시나리오 생성

    시나리오 1: 낙관적 (확률 30%)
    - GDP 성장 가속 (3.5%)
    - 인플레이션 둔화 (2.5%)
    - 기술주 강세
    - 추천: 미국 기술주 40%, 일본 제조업 20%, 중국 성장주 20%, ETF 20%

    시나리오 2: 중립적 (확률 50%)
    - 현상 유지
    - 완만한 성장
    - 추천: 균형 포트폴리오 (미국 30%, 일본 25%, 중국 20%, 채권 ETF 25%)

    시나리오 3: 비관적 (확률 20%)
    - 경기 둔화
    - 금리 인상
    - 추천: 방어주 + 금 + 채권 (미국 방어주 30%, 금 ETF 30%, 채권 40%)
    """
    pass
```

#### 2.3 시나리오 Supabase 저장
```sql
CREATE TABLE investment_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100),
    scenario_type VARCHAR(20),  -- "낙관적", "중립적", "비관적"
    probability FLOAT,  -- 0.0 ~ 1.0
    description TEXT,
    assumptions JSONB,  -- 가정 사항
    asset_allocation JSONB,  -- 자산 배분 제안
    expected_return FLOAT,
    risk_level VARCHAR(20),
    generated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

### Phase 3: 자산 배분 추천 및 추적 시스템

#### 3.1 사용자 포트폴리오 입력
```typescript
// 웹 UI
interface UserPortfolio {
    totalInvestment: number;  // 총 투자 금액
    currentHoldings: {
        ticker: string;
        shares: number;
        averagePrice: number;
        currentValue: number;
    }[];
    cashBalance: number;
    riskTolerance: 'low' | 'medium' | 'high';
}
```

#### 3.2 리밸런싱 제안
```python
def suggest_rebalancing(
    user_portfolio: UserPortfolio,
    selected_scenario: Scenario
) -> RebalancingPlan:
    """
    현재 포트폴리오 vs 선택한 시나리오 권장 배분 비교

    현재: AAPL 30%, TSLA 20%, 삼성전자 30%, 현금 20%
    권장: 미국 기술주 40%, 일본 제조업 20%, 중국 성장주 20%, ETF 20%

    액션:
    - AAPL 유지 (30% -> 25%)
    - TSLA 일부 매도 (20% -> 15%)
    - 7203.T (도요타) 매수 (0% -> 20%)
    - 0700.HK (텐센트) 매수 (0% -> 20%)
    - 삼성전자 전량 매도 (30% -> 0%)
    - QQQ ETF 매수 (0% -> 20%)
    """
    pass
```

#### 3.3 Supabase 추적 테이블
```sql
CREATE TABLE user_portfolios (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    snapshot_date TIMESTAMP DEFAULT NOW(),
    total_value NUMERIC,
    holdings JSONB,
    selected_scenario_id INTEGER REFERENCES investment_scenarios(id),
    cash_balance NUMERIC
);

CREATE TABLE portfolio_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    transaction_date TIMESTAMP DEFAULT NOW(),
    action VARCHAR(10),  -- "BUY", "SELL"
    ticker VARCHAR(20),
    shares NUMERIC,
    price NUMERIC,
    total_value NUMERIC,
    reason TEXT  -- "시나리오 1 선택으로 인한 리밸런싱"
);
```

### Phase 4: 성과 분석 및 학습 시스템

#### 4.1 실제 vs 예측 비교
```python
def analyze_performance(
    scenario_id: int,
    days_elapsed: int
) -> PerformanceReport:
    """
    시나리오 선택 후 N일 경과 시점 성과 분석

    예측 (시나리오 1):
    - 기대 수익률: +8% (3개월)
    - 리스크: 중간

    실제 (3개월 후):
    - 실제 수익률: +6.5%
    - 최대 낙폭: -3%

    평가:
    - 예측 정확도: 81%
    - 리스크 관리: 양호
    - 결론: 성공
    """
    pass
```

#### 4.2 AI 모델 가중치 자동 조정
```python
def update_ai_weights(performance_history: List[PerformanceReport]):
    """
    과거 성과 기반으로 AI 모델 파라미터 조정

    패턴 학습:
    - 블로그 인사이트 중 "반도체" 키워드 → 실제 상승 확률 75%
    - "금리 인상" 키워드 → 기술주 하락 확률 60%

    가중치 업데이트:
    - "반도체" 인사이트 가중치: 0.5 -> 0.75
    - "금리 인상" 부정적 가중치: 0.4 -> 0.6
    """
    pass
```

#### 4.3 Supabase 학습 데이터 저장
```sql
CREATE TABLE scenario_performance (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES investment_scenarios(id),
    user_id UUID REFERENCES auth.users(id),
    selection_date TIMESTAMP,
    evaluation_date TIMESTAMP,
    expected_return FLOAT,
    actual_return FLOAT,
    accuracy_score FLOAT,
    success BOOLEAN,
    lessons_learned TEXT
);

CREATE TABLE ai_model_weights (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100),
    category VARCHAR(50),  -- "블로그", "뉴스", "경제지표"
    weight FLOAT,
    confidence FLOAT,
    last_updated TIMESTAMP DEFAULT NOW(),
    update_reason TEXT
);
```

---

## 📊 데이터 흐름

```
1. 매일 자동 실행 (Cron)
   ├─> 블로그 크롤링 (새 글 수집)
   ├─> 뉴스 RSS 수집
   ├─> 시장 데이터 업데이트
   └─> Supabase 저장

2. 백테스팅 엔진 (주 1회 실행)
   ├─> 과거 블로그 인사이트 추출
   ├─> 실제 시장 데이터와 비교
   ├─> 상관관계 계산
   └─> 신뢰도 업데이트

3. 시나리오 생성 (사용자 요청 시)
   ├─> 현재 경제 상황 분석
   ├─> 백테스팅 결과 참조
   ├─> AI 모델로 3-5개 시나리오 생성
   └─> 확률 계산 및 저장

4. 자산 배분 제안 (시나리오 선택 시)
   ├─> 선택된 시나리오 로드
   ├─> 사용자 포트폴리오 분석
   ├─> 리밸런싱 계획 생성
   └─> 예상 수익률 계산

5. 성과 추적 (매일 자동)
   ├─> 사용자 포트폴리오 스냅샷
   ├─> 실제 수익률 계산
   ├─> 예측과 비교
   └─> 학습 데이터 업데이트

6. AI 모델 개선 (월 1회)
   ├─> 전체 성과 데이터 분석
   ├─> 성공/실패 패턴 학습
   ├─> 가중치 자동 조정
   └─> 다음 시나리오 생성 시 반영
```

---

## 🎨 UI/UX 설계

### 메인 대시보드
```
┌────────────────────────────────────────────────────────┐
│  🌍 AI 지능형 투자 분석 시스템                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  📊 현재 시장 상황                                      │
│  ├─ GDP: 2.5% ↑    인플레이션: 3.2% ↓                 │
│  ├─ VIX: 15.2 (안정)  뉴스 센티먼트: 중립             │
│  └─ 블로그 분위기: 긍정적 (신뢰도 87%)                 │
│                                                        │
│  🎯 AI 생성 투자 시나리오 (백테스팅 검증 완료)          │
│  ┌──────────────────────────────────────────────┐    │
│  │ 시나리오 1: 기술주 강세 시나리오 (확률 35%)   │    │
│  │ 📈 예상 수익: +12% (6개월)                   │    │
│  │ ⚠️ 리스크: 중간                              │    │
│  │ 💡 근거: 반도체 호황, AI 투자 증가          │    │
│  │ 📊 과거 성공률: 78% (백테스팅 50회)          │    │
│  │ [선택하기]                                   │    │
│  └──────────────────────────────────────────────┘    │
│                                                        │
│  ┌──────────────────────────────────────────────┐    │
│  │ 시나리오 2: 안정 성장 시나리오 (확률 50%)     │    │
│  │ 📈 예상 수익: +6% (6개월)                    │    │
│  │ ⚠️ 리스크: 낮음                              │    │
│  │ 💡 근거: 경제 성장 지속, 금리 안정           │    │
│  │ 📊 과거 성공률: 85% (백테스팅 80회)          │    │
│  │ [선택하기]                                   │    │
│  └──────────────────────────────────────────────┘    │
│                                                        │
│  💼 내 포트폴리오                                       │
│  ├─ 총 자산: $100,000                                 │
│  ├─ 현재 수익률: +5.2%                               │
│  └─ [포트폴리오 입력/수정]                            │
│                                                        │
│  📈 과거 성과                                          │
│  ├─ 2024-08 추천 시나리오: 성공 (+8.2%)               │
│  ├─ 2024-09 추천 시나리오: 성공 (+3.1%)               │
│  └─ 전체 성공률: 82% (12개월)                         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 구현 단계

### Phase 1: 백테스팅 시스템 (1-2주)
- [ ] 블로그 데이터 시점별 분할
- [ ] 시장 데이터 수집 (Yahoo Finance API)
- [ ] 인사이트-결과 상관관계 분석
- [ ] Supabase 테이블 생성 및 데이터 저장
- [ ] 백테스팅 결과 시각화 UI

### Phase 2: 시나리오 생성 엔진 (2-3주)
- [ ] 경제 상황 분석 모듈
- [ ] AI 시나리오 생성 알고리즘 (Ollama/OpenAI)
- [ ] 확률 계산 및 리스크 평가
- [ ] Supabase 시나리오 저장
- [ ] 시나리오 선택 UI

### Phase 3: 자산 배분 시스템 (2주)
- [ ] 사용자 포트폴리오 입력 UI
- [ ] 리밸런싱 알고리즘
- [ ] 거래 제안 생성
- [ ] Supabase 포트폴리오 추적
- [ ] 자산 배분 시각화

### Phase 4: 성과 분석 및 학습 (2주)
- [ ] 실제 vs 예측 비교 분석
- [ ] AI 모델 가중치 자동 조정
- [ ] 성과 대시보드
- [ ] 학습 데이터 Supabase 저장
- [ ] 성공/실패 리포트 생성

### Phase 5: 통합 및 최적화 (1주)
- [ ] 전체 시스템 통합 테스트
- [ ] 성능 최적화
- [ ] 에러 처리 강화
- [ ] 문서화

---

## 💡 추가 아이디어

### 1. 소셜 투자 기능
- 다른 사용자들이 선택한 시나리오 통계
- 성공률 높은 사용자 팔로우
- 시나리오별 커뮤니티 토론

### 2. 알림 시스템
- 시나리오 확률 변화 시 알림
- 리밸런싱 권장 시점 알림
- 중요 경제 지표 발표 알림

### 3. 모바일 앱
- React Native 기반
- 푸시 알림
- 간편 포트폴리오 조회

### 4. API 서비스
- 외부 개발자에게 시나리오 API 제공
- 유료 구독 모델

---

## 📝 기술 스택

- **백엔드**: FastAPI, Python 3.12
- **AI**: Ollama (로컬), OpenAI (클라우드)
- **데이터베이스**: Supabase (PostgreSQL + pgvector)
- **프론트엔드**: HTML/CSS/JS (현재), React (향후)
- **데이터 수집**: yfinance, requests, BeautifulSoup
- **백테스팅**: pandas, numpy
- **시각화**: Chart.js
- **배포**: Docker, Linux Server

---

## 🎯 성공 지표 (KPI)

1. **백테스팅 신뢰도**: 인사이트-결과 상관계수 평균 > 0.7
2. **시나리오 정확도**: 예측 vs 실제 수익률 오차 < 20%
3. **사용자 만족도**: 추천 시나리오 채택률 > 60%
4. **성과**: 시스템 추천 포트폴리오 평균 수익률 > 시장 평균
5. **학습 효과**: 월별 예측 정확도 지속 개선

---

이 시스템을 완성하면 **세계 최초의 블로그 인사이트 기반 백테스팅 투자 시스템**이 됩니다!
