# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Environment Setup
```bash
# Activate virtual environment (always run first)
source ai-hedge-env/bin/activate

# Install dependencies with Poetry (initial setup)
poetry install

# Install with trading extras for live trading
poetry install --extras trading
```

### Web Server Execution
```bash
# Main web API server (port 8888)
source ai-hedge-env/bin/activate && python simple_web_api.py

# Alternative web server starter
source ai-hedge-env/bin/activate && python start_web_server.py

# Backend only (port 8000)
source ai-hedge-env/bin/activate && uvicorn app.backend.main:app --host 0.0.0.0 --port 8000

# Frontend development server
cd app/frontend && npm run dev
```

### AI Hedge Fund CLI
```bash
# Run with Poetry
poetry run python src/main.py --ticker AAPL,MSFT,NVDA

# Run with local LLMs (Ollama)
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --ollama

# Show agent reasoning details
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --show-reasoning

# Run backtester
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA

# Start live trading (paper mode)
poetry run python src/live_trading.py --ticker AAPL --mode paper

# Live trading setup
poetry run python src/live_trading.py --setup
```

### Docker Commands
```bash
# Build Docker image
./run.sh build

# Run hedge fund with Docker
./run.sh --ticker AAPL,MSFT,NVDA main

# Run backtester with Docker
./run.sh --ticker AAPL,MSFT,NVDA backtest

# With specific date range
./run.sh --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01 main
```

### Testing & Quality Checks
```bash
# Playwright frontend tests
source ai-hedge-env/bin/activate && python final_test.py

# Direct API tests
source ai-hedge-env/bin/activate && python debug_api_test.py

# Code quality checks
poetry run black src/
poetry run isort src/
poetry run flake8 src/

# Run a single test
poetry run pytest tests/test_specific.py::test_function_name -v
```

## 시스템 아키텍처

### 두 가지 모드의 AI 헤지펀드 시스템

1. **교육용 CLI 시스템** (원본)
   - 15개 AI 에이전트 기반 (Warren Buffett, Ben Graham 등)
   - LangGraph 워크플로우로 순차적 의사결정
   - 백테스팅과 시뮬레이션만 지원

2. **실제 거래 가능 웹 시스템** (확장)
   - Yahoo Finance 실시간 데이터 연동
   - FastAPI 백엔드 + HTML/CSS/JS 프론트엔드
   - JWT 인증 (admin/hedge2024!)
   - AI 자동 종목 선별 및 분석

### 핵심 컴포넌트

#### AI 에이전트 시스템 (`src/agents/`)
- **투자 철학 에이전트들**: warren_buffett.py, ben_graham.py, cathie_wood.py 등
- **분석 전문 에이전트들**: technicals.py, fundamentals.py, sentiment.py, valuation.py
- **매크로 경제 에이전트**: macro_economic_agent.py (경제 지표 분석)
- **리스크 관리**: risk_manager.py, portfolio_manager.py
- **상태 관리**: `src/graph/state.py`에서 LangGraph 워크플로우 상태

#### 실시간 거래 시스템 (`src/brokers/`, `src/execution/`)
- **브로커 인터페이스**: Alpaca Trading, Interactive Brokers 지원
- **거래 엔진**: `trading_engine.py`에서 주문 실행 및 리스크 관리
- **실시간 모니터링**: `risk_monitor.py`에서 포지션 및 리스크 추적

#### 웹 인터페이스
- **FastAPI 백엔드**: `simple_web_api.py` (포트 8888)
- **Yahoo Finance 연동**: `src/tools/yahoo_finance.py`에서 실시간 데이터 및 AI 종목 선별
- **프론트엔드**: `web/index.html`에서 다크 테마 거래 인터페이스

#### 데이터 및 분석 (`src/tools/`)
- **Market 데이터**: `api.py`에서 Financial Datasets API 연동
- **Yahoo Finance**: `yahoo_finance.py`에서 실시간 가격, 재무 지표, 종목 스크리닝
- **경제 지표**: `economic_indicators.py`에서 GDP, 실업률, 인플레이션 등 매크로 데이터
- **한국 주식**: `korean_stocks.py`에서 한국 시장 데이터 (KRX)
- **뉴스 수집**: `news_aggregator.py`에서 RSS 기반 뉴스 수집 및 감성 분석
- **캐싱 시스템**: `src/data/cache.py`에서 API 호출 최적화

### 설정 및 인증

#### 환경 변수 (`.env`)
```
# LLM API 키들 (최소 하나는 필수)
OPENAI_API_KEY=your-openai-api-key
GROQ_API_KEY=your-groq-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
GOOGLE_API_KEY=your-google-api-key

# 금융 데이터 API (AAPL, GOOGL, MSFT, NVDA, TSLA는 무료)
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-api-key

# 웹 인터페이스 인증
WEB_USERNAME=admin
WEB_PASSWORD=hedge2024!

# 브로커 API (실거래용)
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
IB_HOST=127.0.0.1
IB_PORT=7497  # 7497: Paper, 7496: Live

# 알림 설정 (선택사항)
NOTIFICATION_EMAIL=your_email@example.com
SLACK_WEBHOOK=your_slack_webhook_url
```

#### 거래 설정 (`src/config/trading_config.py`)
- 포트폴리오 한도, 리스크 파라미터
- 브로커별 설정 (페이퍼 트레이딩 vs 실거래)

## 주요 특징

### AI 종목 선별 알고리즘
- S&P 500 상위 50개 종목에서 멀티 기준 평가
- 수익률, 변동성, 시가총액, PER 등 종합 점수
- 실시간 Yahoo Finance 데이터 기반 분석
- 한국 주식 지원: KRX 시장 데이터 연동 (6자리 종목 코드 자동 변환)

### 매크로 경제 분석 (신규)
- **경제 지표 통합**: GDP, CPI, 실업률, 금리, 제조업 지수 등
- **매크로 에이전트**: 경제 지표를 기반으로 시장 전망 및 투자 전략 제시
- **뉴스 감성 분석**: RSS 피드 기반 실시간 뉴스 수집 및 감성 점수 계산

### 💼 AI 포트폴리오 분산투자 제안 (신규)
- **1억원 기준 자동 자산배분**: 투자 금액을 입력하면 AI가 최적 포트폴리오 자동 생성
- **10개 종목 분산투자**: AI 점수 기반으로 자동으로 비중 조정
- **실시간 계산**: 현재가 기준 실제 매수 가능 주식 수 및 금액 계산
- **리스크 분석**: 포트폴리오 전체의 예상 수익률, 변동성, 리스크 수준 제공
- **API 엔드포인트**: `/api/portfolio-suggestion` (POST)
- **웹 UI**: 헤더의 "포트폴리오 제안" 버튼 클릭

### 📈 포트폴리오 백테스팅 (신규)
- **과거 3개월 수익률 시뮬레이션**: 제안된 포트폴리오를 3개월 전에 투자했다면 현재까지 수익률 곡선 표시
- **실시간 차트**: Chart.js 기반 인터랙티브 수익률 곡선 차트
- **성과 지표**: 총 수익률, 변동성, 최대 낙폭(MDD), 샤프 비율 계산
- **종목별 분석**: 각 종목의 개별 수익률 및 가격 변화 표시
- **API 엔드포인트**: `/api/portfolio-backtest` (POST)
- **웹 UI**: 포트폴리오 생성 후 "과거 3개월 수익률 보기" 버튼
- **E2E 테스트**: `test_portfolio_backtest.py` (Playwright 기반)

### 안전한 거래 시스템
- 4단계 안전 장치: 페이퍼 트레이딩 → 드라이 런 → 수동 승인 → 자동 거래
- 실시간 리스크 모니터링 및 포지션 한도 관리
- JWT 기반 웹 인증 시스템

### 멀티 브로커 지원
- Alpaca Trading (주식, ETF)
- Interactive Brokers (글로벌 시장)
- 통합 인터페이스로 브로커 간 전환 가능

## 개발 규칙

### 파일 구조 규칙
- AI 에이전트: `src/agents/`에 투자자 이름으로 (예: warren_buffett.py)
- 거래 관련: `src/brokers/` (브로커 인터페이스), `src/execution/` (거래 엔진)
- 웹 API: `simple_web_api.py` (개발/테스트용), `app/backend/` (프로덕션용, 현재 미사용)
- 설정 파일: `.env` (API 키, 로컬 전용), `src/config/trading_config.py` (거래 설정)
- 데이터 도구: `src/tools/` (api.py, yahoo_finance.py 등)
- LangGraph 상태: `src/graph/state.py` (AgentState 정의 및 워크플로우 관리)

### 코드 스타일
- Black 포매터: line-length 420 (매우 긴 라인 허용)
- 한국어 주석 및 로그 메시지 허용
- 타입 힌트 필수 (typing 모듈 사용)
- Pydantic 모델을 사용하여 LLM 응답 구조화

### 안전 장치 및 거래 모드
1. **Dry Run** (`trading.dry_run=True`): 모든 거래가 시뮬레이션으로만 실행
2. **Paper Trading** (`broker.paper_trading=True`): 브로커의 모의 계좌 사용
3. **Manual Approval** (`trading.auto_trading=False`): 모든 거래를 수동 승인
4. **Auto Trading** (`trading.auto_trading=True`): 자동 거래 실행 (위험!)

**중요**: 실거래 전 반드시 dry_run과 paper_trading부터 시작하여 단계적으로 테스트

### 테스트 전략
- Playwright로 웹 인터페이스 E2E 테스트 (final_test.py, debug_api_test.py)
- 실제 API 호출 전에 페이퍼 트레이딩으로 검증
- Yahoo Finance 연동은 실시간 데이터로 테스트
- 백테스팅(`src/backtester.py`)으로 전략 검증 후 라이브 트레이딩 시작

## 접속 정보

### ⭐ 주요 접속 주소 (우선순위 순)
1. **http://192.168.1.3:8888** ✅ (네트워크 접속 - 가장 안정적)
2. **http://127.0.0.1:8888** (로컬 접속)
3. **http://localhost:8888** (로컬 접속 대체)

### 로그인 정보
- **사용자명**: admin
- **비밀번호**: hedge2024!

### API 문서
- **Swagger UI**: http://192.168.1.3:8888/docs (FastAPI 자동 생성)

## LangGraph 워크플로우

### 에이전트 실행 순서
15개 AI 에이전트가 LangGraph를 통해 순차적으로 실행되며, 각 에이전트의 출력이 다음 에이전트의 입력으로 사용됩니다. `src/graph/state.py`의 `AgentState`가 전체 워크플로우 상태를 관리합니다.

### AgentState 구조
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    data: Annotated[dict[str, any], merge_dicts]  # 에이전트 간 데이터 공유
    metadata: Annotated[dict[str, any], merge_dicts]  # 메타데이터
```

### 주요 에이전트 간 상호작용
- **투자 철학 에이전트들** (warren_buffett, peter_lynch 등) → **분석 에이전트들** (fundamentals, technicals, sentiment, valuation) → **매크로 경제 에이전트** → **리스크 매니저** → **포트폴리오 매니저**
- 각 에이전트는 독립적인 분석을 수행하고 결과를 `state["data"]`에 저장
- 최종적으로 포트폴리오 매니저가 모든 분석을 종합하여 거래 결정
- `--show-reasoning` 플래그 사용 시 `show_agent_reasoning()` 함수가 각 에이전트의 추론 과정을 출력

### 새로운 에이전트 추가 방법
1. `src/agents/` 디렉토리에 새 에이전트 파일 생성 (예: `new_agent.py`)
2. `src/utils/llm.py`의 `call_llm()` 함수를 사용하여 LLM 호출
3. 에이전트 출력은 반드시 Pydantic 모델로 구조화
4. 에이전트 간 데이터 공유는 `AgentState.data` 딕셔너리 사용
5. `src/graph/state.py`에 필요한 상태 추가 (선택사항)
6. LangGraph 워크플로우에 에이전트 노드 추가

## 프로젝트별 설정

### Black 포매터 설정
- **Line Length**: 420 (일반적인 88보다 매우 길게 설정됨)
- **Target Version**: Python 3.11
- 한 줄에 많은 코드를 허용하므로 주의 필요

### Import 정렬 (isort)
- Black과 호환되는 프로파일 사용
- 섹션 내에서 알파벳순 정렬 강제

### 지원되는 LLM 프로바이더
- OpenAI (gpt-4o, gpt-4o-mini)
- Anthropic (claude-3-5-sonnet, claude-3-opus)
- Google (gemini-2.0-flash, gemini-2.0-pro)
- Groq (llama3, deepseek 등)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Ollama (로컬 실행)

**참고**: `src/utils/llm.py`의 `call_llm()` 함수가 모든 LLM 호출을 처리하며, JSON 모드 지원 여부에 따라 자동으로 처리 방식을 선택합니다.

### 모델 선택 및 LLM 관련 코드 작업 시 주의사항
- LLM 호출 시 반드시 `src/utils/llm.py`의 `call_llm()` 함수 사용
- 새로운 에이전트 추가 시 `src/graph/state.py`의 `AgentState`에 상태 추가 필요
- 에이전트 간 데이터 전달은 `AgentState.data` 딕셔너리를 통해 수행
- JSON 모드 미지원 모델(일부 Ollama 모델)의 경우 자동으로 마크다운에서 JSON 추출

## 데이터 소스 및 API 제한사항

### Yahoo Finance (`yfinance`)
- **무료 제한**: 무제한 사용 가능하지만 rate limiting 존재
- **데이터 범위**: 글로벌 주식, ETF, 뮤추얼 펀드, 암호화폐
- **한국 주식**: `.KS` (KOSPI), `.KQ` (KOSDAQ) 접미사 사용 (예: `005930.KS` = 삼성전자)
- **주의사항**: 6자리 종목 코드는 자동으로 `.KS` 추가 변환

### Financial Datasets API
- **무료 티커**: AAPL, GOOGL, MSFT, NVDA, TSLA (API 키 불필요)
- **유료 티커**: 기타 모든 종목 (API 키 필요)
- **데이터 종류**: 실시간 가격, 재무제표, 밸류에이션 지표

### 경제 지표 API
- **소스**: FRED (Federal Reserve Economic Data), World Bank
- **데이터**: GDP, CPI, 실업률, 금리, PMI 등
- **업데이트 주기**: 월별/분기별 (실시간 아님)

### 뉴스 데이터
- **소스**: RSS 피드 (Google News, Yahoo Finance News)
- **무료 사용**: 제한 없음
- **감성 분석**: 내장된 감성 분석 알고리즘 사용