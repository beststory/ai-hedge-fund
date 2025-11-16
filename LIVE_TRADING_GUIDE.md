# AI 헤지펀드 실제 거래 시스템 가이드

이 가이드는 AI 헤지펀드 시스템을 실제 미국 주식 거래에 사용하는 방법을 설명합니다.

## ⚠️ 중요 경고

**이 시스템을 실제 거래에 사용하기 전에 반드시 다음 사항을 확인하세요:**

1. **페이퍼 트레이딩으로 충분히 테스트**
2. **리스크 관리 설정 점검**
3. **소액으로 시작**
4. **지속적인 모니터링**

## 목차

1. [초기 설정](#초기-설정)
2. [브로커 설정](#브로커-설정)
3. [실행 방법](#실행-방법)
4. [안전 장치](#안전-장치)
5. [문제 해결](#문제-해결)

## 초기 설정

### 1. 의존성 설치

```bash
# Poetry 사용 (권장)
poetry install --extras trading

# 또는 pip 사용
pip install -r requirements.txt
pip install ib-insync  # Interactive Brokers 사용시에만
```

### 2. 설정 파일 생성

```bash
python src/live_trading.py --setup
```

이 명령으로 다음 파일들이 생성됩니다:
- `config/trading_config.yaml`: 거래 설정
- `.env.example`: 환경변수 예제

### 3. API 키 설정

`.env.example`을 `.env`로 복사하고 다음 값들을 설정하세요:

```env
# Alpaca (권장 초보자용)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key

# OpenAI (AI 분석용)
OPENAI_API_KEY=your_openai_api_key

# 금융 데이터 (기본 티커들은 무료)
FINANCIAL_DATASETS_API_KEY=your_financial_datasets_api_key

# 알림 (선택사항)
NOTIFICATION_EMAIL=your_email@example.com
SLACK_WEBHOOK=your_slack_webhook_url
```

## 브로커 설정

### Alpaca (권장 초보자용)

**장점:**
- 무료 페이퍼 트레이딩
- 간단한 API
- 낮은 최소 계좌 금액

**설정:**
1. [Alpaca](https://alpaca.markets/)에서 계정 생성
2. Paper Trading API 키 발급
3. `.env` 파일에 키 입력

### Interactive Brokers (고급 사용자용)

**장점:**
- 낮은 수수료
- 다양한 상품 지원
- 전문적인 도구

**설정:**
1. Interactive Brokers 계정 생성
2. TWS(Trader Workstation) 또는 IB Gateway 설치
3. API 설정 활성화
4. 포트 설정 (7497: Paper, 7496: Live)

```yaml
# config/trading_config.yaml
broker:
  name: "ib"
  paper_trading: true
  host: "127.0.0.1"
  port: 7497
```

## 실행 방법

### 1. 대화형 모드 (권장)

```bash
python src/live_trading.py
```

메뉴에서 다음 옵션들을 선택할 수 있습니다:
- **단일 분석 실행**: 한 번만 분석하고 거래
- **연속 거래 모드**: 자동으로 반복 실행
- **계좌 상태 확인**: 현재 포지션과 손익 확인
- **리스크 체크**: 위험 요소 점검
- **설정 관리**: 시스템 설정 변경

### 2. 단일 실행 모드

```bash
python src/live_trading.py --mode single --tickers AAPL,GOOGL,MSFT,NVDA
```

### 3. 연속 거래 모드

```bash
python src/live_trading.py --mode continuous --tickers AAPL,GOOGL,MSFT,NVDA --interval 60
```

## 설정 옵션

### 주요 설정 항목

```yaml
# config/trading_config.yaml

# 브로커 설정
broker:
  name: "alpaca"          # "alpaca" 또는 "ib"
  paper_trading: true     # 페이퍼 트레이딩 (실제 거래: false)

# 거래 설정
trading:
  dry_run: true           # 시뮬레이션 모드 (실제 주문: false)
  auto_trading: false     # 자동 거래 실행
  market_hours_only: true # 장중에만 거래
  max_daily_trades: 50    # 일일 최대 거래 수

# 리스크 관리
risk:
  max_position_size: 0.1     # 단일 포지션 최대 비중 (10%)
  max_sector_exposure: 0.3   # 섹터별 최대 노출 (30%)
  min_confidence: 0.7        # 최소 신뢰도 (70%)
  max_drawdown: 0.15         # 최대 드로우다운 (15%)

# AI 설정
ai:
  model_name: "gpt-4o"
  selected_analysts:
    - "warren_buffett"
    - "peter_lynch"
    - "fundamentals"
    - "technicals"
```

## 안전 장치

### 1. 다단계 안전 시스템

1. **페이퍼 트레이딩**: 실제 돈 없이 테스트
2. **드라이런 모드**: 주문 실행 없이 시뮬레이션
3. **리스크 체크**: 모든 거래 전 위험 평가
4. **포지션 제한**: 과도한 집중 방지
5. **긴급 정지**: 위험 상황시 전체 포지션 청산

### 2. 자동 모니터링

시스템은 다음 위험 요소들을 자동으로 모니터링합니다:
- 포지션 집중도 (단일 종목 과투자)
- 유동성 (현금 보유량 부족)
- 변동성 (급격한 가격 변동)
- 상관관계 (종목간 높은 상관성)
- 드로우다운 (포트폴리오 손실)

### 3. 알림 시스템

위험 상황 발생시 다음과 같은 알림을 받을 수 있습니다:
- 이메일 알림
- Slack 알림
- 콘솔 출력

## 실전 사용 가이드

### 1. 단계별 접근

**1단계: 페이퍼 트레이딩**
```yaml
broker:
  paper_trading: true
trading:
  dry_run: true
  auto_trading: false
```

**2단계: 실제 브로커 + 드라이런**
```yaml
broker:
  paper_trading: false
trading:
  dry_run: true        # 여전히 시뮬레이션
  auto_trading: false
```

**3단계: 수동 실제 거래**
```yaml
broker:
  paper_trading: false
trading:
  dry_run: false       # 실제 주문 실행
  auto_trading: false  # 수동 승인 필요
```

**4단계: 자동 거래 (매우 주의)**
```yaml
broker:
  paper_trading: false
trading:
  dry_run: false
  auto_trading: true   # 완전 자동화
```

### 2. 권장 운영 방법

1. **소액으로 시작**: $1,000-$5,000 정도
2. **지속적인 모니터링**: 처음 몇 주간은 매일 확인
3. **점진적 증액**: 안정적인 성과 확인 후 증액
4. **정기적인 백테스트**: 전략의 유효성 지속 확인

### 3. 위험 관리 체크리스트

- [ ] 페이퍼 트레이딩으로 최소 1개월 테스트
- [ ] 손실 한도 설정 (일일, 월간, 연간)
- [ ] 포지션 크기 제한 설정
- [ ] 긴급 정지 절차 숙지
- [ ] 백업 계획 수립
- [ ] 세금 영향 고려

## 모니터링 및 분석

### 1. 실시간 모니터링

```bash
# 리스크 체크
python -c "
from src.live_trading import LiveTradingSystem
system = LiveTradingSystem()
system.initialize()
print(system.risk_monitor.run_risk_check())
"
```

### 2. 성과 분석

시스템은 다음 지표들을 추적합니다:
- 총 수익률
- 샤프 비율
- 최대 드로우다운
- 승률
- 일일/월간 변동성

### 3. 로그 분석

모든 거래와 의사결정 과정이 `trading.log`에 기록됩니다.

## 문제 해결

### 일반적인 문제들

**1. 브로커 연결 실패**
```
브로커 인증 실패
```
- API 키 확인
- 네트워크 연결 확인
- 브로커 서비스 상태 확인

**2. 시장 개장시간 문제**
```
시장이 개장하지 않아 거래할 수 없습니다
```
- `market_hours_only: false`로 설정 (주의!)
- 또는 시장 개장시간에 실행

**3. 리스크 체크 실패**
```
리스크 체크 실패: 포지션 크기 초과
```
- 리스크 설정 조정
- 포지션 크기 축소

### 로그 확인

```bash
# 최근 거래 로그 확인
tail -f trading.log

# 오류 로그만 확인  
grep ERROR trading.log
```

### 긴급 상황 대응

**전체 포지션 청산이 필요한 경우:**

```bash
python -c "
from src.live_trading import LiveTradingSystem
system = LiveTradingSystem()
system.initialize()
system.emergency_stop()
"
```

## 법적 고지사항

- 이 소프트웨어는 교육 목적으로 제공됩니다
- 실제 투자 결과에 대한 보장은 없습니다
- 투자 손실에 대한 책임은 사용자에게 있습니다
- 투자 전 전문가와 상담하시기 바랍니다

## 지원

문제가 발생하면 다음 순서로 확인하세요:

1. 이 가이드의 문제 해결 섹션 확인
2. 로그 파일 분석
3. GitHub Issues에 문제 리포트

**도움이 필요하면 언제든지 물어보세요!**