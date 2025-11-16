# 🔥 트렌딩 종목 추천 시스템 구현 계획

## 📋 개요

**목표**: 뉴스/SNS 기반 "고위험 고수익" 트렌딩 종목 추천 시스템 구축

**기존 시스템과 차별점**:
- 기존 AI 추천: 안정적인 대형주 (구글, 엔비디아, 테슬라 등)
- 신규 트렌딩: 급부상 중인 테마주 (양자컴퓨터, 전쟁 관련, 트럼프 관련 등)

---

## 🎯 핵심 기능

### 1. 트렌딩 키워드 기반 종목 발굴
**테마별 분류**:
- **양자컴퓨터**: IonQ (IONQ), Rigetti Computing (RGTI), D-Wave Quantum (QBTS)
- **전쟁/방산**: Lockheed Martin (LMT), Northrop Grumman (NOC), Raytheon (RTX)
- **에너지/자원**: Chevron (CVX), Exxon (XOM), Uranium Energy (UEC)
- **트럼프 관련**: Texas Pacific Land (TPL), Energy Transfer (ET), Continental Resources (CLR)
- **AI 칩 소형주**: Marvell (MRVL), ARM Holdings (ARM), Broadcom (AVGO)
- **우주/위성**: SpaceX 관련, Rocket Lab (RKLB), AST SpaceMobile (ASTS)

### 2. 종목 선정 기준
1. **급등 여부**: 최근 1-3개월 수익률 > 20%
2. **뉴스 활성도**: 최근 1주일 관련 뉴스 > 5건
3. **변동성**: 일일 변동성 > 3% (고위험 고수익)
4. **시가총액**: $500M ~ $50B (중소형주 중심)
5. **거래량 급증**: 최근 평균 거래량 대비 1.5배 이상

### 3. 상세 정보 제공
- **현재 가격**: 실시간 Yahoo Finance
- **가격 변화**: 1주일, 1개월, 3개월, 6개월, 1년
- **관련 뉴스**: 최근 10개 뉴스 (제목 + 링크 + 날짜)
- **트렌딩 이유**: AI 분석 기반 추천 근거
- **리스크 경고**: 변동성, 유동성 등 위험 요소

---

## 🏗️ 시스템 아키텍처

### 백엔드 (FastAPI)

#### 1. 트렌딩 종목 스크리닝 API
```
GET /api/trending-stocks
Response: {
  "success": true,
  "stocks": [
    {
      "ticker": "IONQ",
      "name": "IonQ Inc.",
      "current_price": 12.50,
      "change_1w": 15.2,
      "change_1m": 45.8,
      "change_3m": 120.5,
      "theme": "양자컴퓨터",
      "risk_level": "high",
      "trending_score": 85,
      "news_count": 12
    },
    ...
  ]
}
```

#### 2. 종목별 상세 분석 API
```
POST /api/trending-analysis
Request: { "symbol": "IONQ" }
Response: {
  "success": true,
  "symbol": "IONQ",
  "name": "IonQ Inc.",
  "current_price": 12.50,
  "price_history": {
    "1w": { "start": 10.85, "end": 12.50, "change": 15.2 },
    "1m": { "start": 8.57, "end": 12.50, "change": 45.8 },
    "3m": { "start": 5.67, "end": 12.50, "change": 120.5 },
    "6m": { "start": 4.20, "end": 12.50, "change": 197.6 },
    "1y": { "start": 3.10, "end": 12.50, "change": 303.2 }
  },
  "theme": "양자컴퓨터",
  "trending_reason": "구글 Willow 칩 발표 이후 양자컴퓨터 관련주 급등. IonQ는 상업용 양자컴퓨터 선두주자로 주목받고 있음.",
  "risk_factors": [
    "높은 변동성 (일일 5-10% 등락)",
    "낮은 유동성",
    "실적 적자 지속"
  ],
  "related_news": [
    {
      "title": "IonQ signs $54.5M deal with U.S. Air Force",
      "url": "...",
      "date": "2025-10-10",
      "source": "Reuters"
    },
    ...
  ],
  "technical_indicators": {
    "volatility": 8.5,
    "volume_ratio": 2.3,
    "rsi": 72
  }
}
```

### 프론트엔드

#### 1. 새로운 탭 추가
```
AI 추천 | KOSPI | NASDAQ | 🔥 트렌딩
```

#### 2. 트렌딩 종목 리스트 UI
- 종목 심볼 + 이름
- 현재 가격
- 1개월 수익률 (색상 코딩)
- 테마 배지 (양자컴퓨터, 방산, 에너지 등)
- 트렌딩 스코어 (0-100)

#### 3. 상세 페이지 (클릭 시)
- **가격 차트**: 6개월 가격 변화 (Chart.js)
- **수익률 테이블**: 1주일/1개월/3개월/6개월/1년
- **트렌딩 이유**: AI 분석 텍스트
- **리스크 경고**: 눈에 띄는 경고 박스
- **관련 뉴스**: 스크롤 가능한 뉴스 리스트

---

## 🛠️ 구현 단계

### Phase 1: 데이터 수집 및 분석 엔진 (2-3시간)
1. **트렌딩 키워드 정의**
   - 수동 큐레이션: 양자컴퓨터, 전쟁, 에너지, 트럼프 등
   - 각 테마별 대표 종목 리스트 작성

2. **종목 스크리닝 알고리즘**
   - Yahoo Finance API로 가격 데이터 수집
   - 수익률 계산 (1w, 1m, 3m, 6m, 1y)
   - 변동성 및 거래량 분석

3. **뉴스 수집**
   - 기존 news_aggregator.py 활용
   - 종목별 관련 뉴스 필터링

### Phase 2: 백엔드 API 구현 (1-2시간)
1. `/api/trending-stocks` 엔드포인트
2. `/api/trending-analysis` 엔드포인트
3. 캐싱 (1시간 TTL)

### Phase 3: 프론트엔드 구현 (2-3시간)
1. 탭 추가 (🔥 트렌딩)
2. 종목 리스트 UI (테마 배지, 수익률 색상)
3. 상세 분석 페이지

### Phase 4: 테스트 및 검증 (1시간)
1. E2E 테스트
2. 실제 데이터 검증
3. 사용자 시나리오 테스트

---

## 📊 예상 종목 리스트 (초기 버전)

### 양자컴퓨터 테마
- IONQ (IonQ Inc.)
- RGTI (Rigetti Computing)
- QBTS (D-Wave Quantum)

### 방산/전쟁 테마
- LMT (Lockheed Martin)
- NOC (Northrop Grumman)
- RTX (Raytheon Technologies)
- BA (Boeing)

### 에너지/자원 테마
- UEC (Uranium Energy Corp)
- CCJ (Cameco Corporation)
- XOM (Exxon Mobil)
- CVX (Chevron)

### 트럼프 관련 테마
- TPL (Texas Pacific Land)
- ET (Energy Transfer)
- CLR (Continental Resources)
- DJT (Trump Media & Technology)

### AI 칩 소형주
- MRVL (Marvell Technology)
- ARM (ARM Holdings)
- SMCI (Super Micro Computer)

### 우주/위성 테마
- RKLB (Rocket Lab)
- ASTS (AST SpaceMobile)
- PL (Planet Labs)

---

## 🚨 리스크 관리

### 사용자 경고 메시지
```
⚠️ 트렌딩 종목은 높은 변동성과 리스크를 동반합니다.
- 단기 급등 후 급락 가능성
- 뉴스 기반 과대평가 위험
- 소액 투자 권장 (포트폴리오의 5-10% 이하)
```

### UI 디자인
- 빨간색/주황색 테마 (위험 강조)
- 트렌딩 스코어 시각화
- 리스크 레벨 표시 (High/Very High)

---

## 🎯 성공 지표

1. **종목 다양성**: 최소 15-20개 트렌딩 종목
2. **뉴스 연관성**: 각 종목당 5개 이상 관련 뉴스
3. **데이터 정확성**: 가격 및 수익률 100% 정확
4. **UI/UX**: 3초 이내 로딩, 직관적인 리스크 표시
5. **사용자 피드백**: 트렌딩 이유가 명확하고 설득력 있음

---

## 📅 예상 일정

- **Phase 1**: 데이터 수집/분석 엔진 (현재)
- **Phase 2**: 백엔드 API (다음)
- **Phase 3**: 프론트엔드 UI (이후)
- **Phase 4**: 테스트/검증 (최종)

**총 소요 시간**: 6-9시간
