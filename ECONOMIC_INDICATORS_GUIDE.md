# 경제지표 및 뉴스 통합 가이드

AI 헤지펀드 시스템에 미국과 한국의 경제지표, 그리고 실시간 뉴스 분석 기능이 통합되었습니다.

## 🌐 새로운 기능

### 1. 거시경제 분석 에이전트
- **Macro Economic Analyst**: 글로벌 경제지표와 뉴스를 종합 분석하여 투자 전략을 제시합니다.

### 2. 경제지표 수집
#### 미국 경제지표 (FRED API)
- GDP (국내총생산)
- CPI (소비자물가지수)
- 실업률
- 연방기금금리
- 10년물 국채수익률
- 소비자신뢰지수
- 산업생산지수
- 주택착공건수
- 무역수지
- 소매판매

#### 한국 경제지표 (한국은행 ECOS API)
- GDP 성장률
- 소비자물가상승률
- 실업률
- 기준금리
- 수출액/수입액
- 경상수지
- 생산자물가지수
- 종합주가지수 (코스피)
- 원/달러 환율

### 3. 뉴스 통합 및 감성 분석
- News API를 통한 글로벌 뉴스 수집
- RSS 피드를 통한 한국/미국 경제 뉴스
- 자동 감성 분석 (긍정/부정/중립)
- 뉴스 기반 시장 심리 파악

### 4. 시장 상황 종합 분석
- 경제지표 기반 시장 전망 (Bullish/Bearish/Neutral)
- 리스크 레벨 평가 (Low/Medium/High)
- 투자 기회 및 위험 요인 식별

## 📦 설치 및 설정

### 1. 필요한 패키지 설치

Poetry를 사용하는 경우:
```bash
poetry add feedparser
```

pip를 사용하는 경우:
```bash
pip install feedparser
```

### 2. API 키 설정

`.env` 파일에 다음 API 키들을 추가하세요 (모두 선택사항):

```env
# FRED API (미국 경제지표)
# https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료로 발급
FRED_API_KEY=your-fred-api-key

# 한국은행 경제통계시스템 (ECOS)
# https://ecos.bok.or.kr/ 에서 무료로 발급
ECOS_API_KEY=your-ecos-api-key

# News API (글로벌 뉴스)
# https://newsapi.org/ 에서 무료 플랜 사용 가능
NEWS_API_KEY=your-news-api-key
```

**참고**: API 키가 없어도 시스템은 샘플 데이터로 작동합니다!

## 🚀 사용 방법

### CLI에서 거시경제 에이전트 사용

```bash
# 거시경제 분석 포함하여 실행
poetry run python src/main.py --ticker AAPL,MSFT,NVDA

# 에이전트 선택 시 "Macro Economic Analyst" 선택
```

### 웹 API 엔드포인트

#### 1. 경제지표 조회
```bash
# 모든 경제지표
curl http://localhost:8888/api/economic-indicators

# 미국 경제지표만
curl http://localhost:8888/api/economic-indicators?country=US

# 한국 경제지표만
curl http://localhost:8888/api/economic-indicators?country=KR
```

#### 2. 시장 상황 분석
```bash
curl http://localhost:8888/api/market-condition
```

응답 예시:
```json
{
  "success": true,
  "condition": {
    "overall_sentiment": "bullish",
    "risk_level": "medium",
    "key_indicators": {...},
    "analysis": "✓ 미국 실업률 양호 (3.8%)\n✓ 소비자 신뢰 양호 (102.6)",
    "timestamp": "2025-10-06T..."
  }
}
```

#### 3. 최근 뉴스 조회
```bash
# 모든 뉴스
curl http://localhost:8888/api/news

# 특정 카테고리만
curl "http://localhost:8888/api/news?categories=미국경제,한국경제&days=3&limit=20"
```

응답 예시:
```json
{
  "success": true,
  "count": 20,
  "news": [...],
  "sentiment": {
    "overall": "positive",
    "distribution": {
      "positive": 12,
      "negative": 3,
      "neutral": 5
    },
    "positive_ratio": 60.0,
    "negative_ratio": 15.0,
    "neutral_ratio": 25.0
  }
}
```

#### 4. 거시경제 대시보드 (통합 데이터)
```bash
curl http://localhost:8888/api/macro-dashboard
```

이 엔드포인트는 한 번의 호출로:
- 미국/한국 경제지표
- 시장 상황 분석
- 최근 뉴스 및 감성 분석

을 모두 제공합니다.

## 📊 프론트엔드 대시보드

웹 인터페이스(`http://localhost:8888`)에 새로운 섹션들이 추가됩니다:

1. **경제지표 대시보드**
   - 실시간 경제지표 모니터링
   - 미국/한국 지표 비교
   - 시계열 차트

2. **시장 상황 분석**
   - 현재 시장 심리 (Bullish/Bearish/Neutral)
   - 리스크 레벨 인디케이터
   - 주요 요인 분석

3. **뉴스 피드**
   - 최신 경제 뉴스
   - 감성 분석 결과
   - 카테고리별 필터링

## 🔧 커스터마이징

### RSS 피드 추가

`src/tools/news_aggregator.py` 파일에서 RSS 피드를 추가할 수 있습니다:

```python
self.rss_feeds = {
    "미국경제": [
        "https://your-custom-feed-url.xml",
        # 추가 RSS 피드들...
    ],
    # ...
}
```

### 경제지표 추가

`src/tools/economic_indicators.py` 파일에서 새로운 지표를 추가할 수 있습니다:

```python
fred_series = {
    "새로운지표": "FRED_SERIES_ID",
    # ...
}
```

## 💡 활용 예시

### 1. 금리 인상기 전략
시스템이 연방기금금리 상승을 감지하면:
- 금융주에 대한 긍정적 신호
- 성장주에 대한 부정적 신호
- 채권 수익률 변동 고려

### 2. 환율 변동 대응
원/달러 환율 급등 감지 시:
- 수출주에 대한 긍정적 신호
- 수입 의존 기업에 대한 리스크 경고
- 글로벌 포트폴리오 재조정 제안

### 3. 뉴스 기반 빠른 대응
중요 경제 뉴스 감지 시:
- 실시간 감성 분석
- 관련 종목 영향도 평가
- 포지션 조정 제안

## 📈 성능 최적화

### 캐싱
- 경제지표는 하루 단위로 캐싱
- 뉴스는 1시간 단위로 캐싱
- API 호출 최소화

### 비동기 처리
모든 데이터 수집은 비동기로 처리되어 성능 최적화됩니다.

## 🛠️ 트러블슈팅

### Q: API 키 없이 사용 가능한가요?
**A**: 네! API 키가 없으면 샘플 데이터로 작동합니다. 하지만 실시간 데이터를 위해서는 API 키 설정을 권장합니다.

### Q: FRED API 키는 어떻게 발급받나요?
**A**: 
1. https://fred.stlouisfed.org/ 방문
2. 무료 계정 생성
3. API Keys 메뉴에서 발급

### Q: 한국은행 API는 어떻게 사용하나요?
**A**:
1. https://ecos.bok.or.kr/ 방문
2. 회원가입 후 로그인
3. 인증키 신청 메뉴에서 발급

### Q: News API 요청 제한은?
**A**: 무료 플랜은 일일 100회 요청 제한이 있습니다. RSS 피드는 제한이 없습니다.

## 📚 참고 자료

- [FRED API 문서](https://fred.stlouisfed.org/docs/api/)
- [한국은행 ECOS API](https://ecos.bok.or.kr/api/)
- [News API 문서](https://newsapi.org/docs)
- [feedparser 문서](https://pythonhosted.org/feedparser/)

## 🎯 향후 계획

- [ ] 더 많은 국가 경제지표 추가
- [ ] 머신러닝 기반 경제지표 예측
- [ ] 실시간 알림 시스템
- [ ] 경제지표 간 상관관계 분석
- [ ] 자동 거래 전략 백테스팅

## 📞 지원

문제가 발생하면 GitHub Issues에 보고해주세요!


