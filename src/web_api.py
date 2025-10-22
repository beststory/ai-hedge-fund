"""웹 인터페이스용 FastAPI 백엔드"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

from src.config.trading_config import get_config, save_config, ConfigManager
from src.brokers.factory import BrokerFactory
from src.execution.trading_engine import TradingEngine, RiskLimits
from src.risk_management.risk_monitor import RiskMonitor
from src.main import run_hedge_fund
from src.websocket_manager import manager, RealTimeMonitor, handle_websocket_message, real_time_monitor
from src.auth import AuthManager, get_current_user, get_current_user_optional, init_auth, get_login_info, ACCESS_TOKEN_EXPIRE_MINUTES
from src.tools.economic_indicators import get_economic_indicators, get_market_condition
from src.tools.news_aggregator import get_recent_news, analyze_news_sentiment


# 전역 변수
app_state = {
    "broker": None,
    "trading_engine": None,
    "risk_monitor": None,
    "config": None,
    "last_analysis": None,
    "trading_history": [],
    "system_status": "stopped"
}

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic 모델들
class TradingRequest(BaseModel):
    tickers: List[str]
    mode: str = "single"  # single, continuous
    interval_minutes: int = 60


class ConfigUpdate(BaseModel):
    section: str
    key: str
    value: Any


class LoginRequest(BaseModel):
    username: str
    password: str


class SystemStatus(BaseModel):
    status: str
    broker_connected: bool
    paper_trading: bool
    dry_run: bool
    auto_trading: bool
    last_update: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작시 설정 로드
    try:
        app_state["config"] = get_config()
        logger.info("설정 로드 완료")
        
        # 인증 시스템 초기화
        init_auth()
        
    except Exception as e:
        logger.error(f"설정 로드 실패: {e}")
    
    yield
    
    # 종료시 정리
    if app_state["broker"]:
        logger.info("브로커 연결 종료")


app = FastAPI(
    title="AI 헤지펀드 거래 시스템",
    description="웹 기반 AI 헤지펀드 거래 및 모니터링 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 정적 파일 서비스 (프론트엔드)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


# 인증 관련 엔드포인트
@app.post("/api/login")
async def login(request: LoginRequest):
    """로그인"""
    user = AuthManager.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 사용자명 또는 비밀번호"
        )
    
    access_token = AuthManager.create_access_token(data={"sub": user["username"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@app.post("/api/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """로그아웃"""
    # 토큰 무효화는 클라이언트에서 토큰 삭제로 처리
    return {"message": "로그아웃되었습니다"}


@app.get("/api/login-info")
async def login_info():
    """로그인 정보 (개발용)"""
    return get_login_info()


@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지"""
    try:
        with open("web/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
            <head><title>AI 헤지펀드</title></head>
            <body>
                <h1>AI 헤지펀드 거래 시스템</h1>
                <p>웹 인터페이스를 초기화하는 중입니다...</p>
                <p>API 엔드포인트: <a href="/docs">/docs</a></p>
                <p><strong>기본 로그인:</strong></p>
                <p>ID: admin, PW: hedge2024!</p>
            </body>
        </html>
        """)


@app.get("/iqc", response_class=HTMLResponse)
@app.get("/iqc.html", response_class=HTMLResponse)
async def iqc_page():
    """IQC 전략 페이지"""
    try:
        with open("web/iqc.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="IQC 페이지를 찾을 수 없습니다")


@app.get("/api/status")
async def get_status() -> SystemStatus:
    """시스템 상태 조회"""
    config = app_state.get("config")
    broker_connected = app_state.get("broker") is not None
    
    if config:
        return SystemStatus(
            status=app_state.get("system_status", "stopped"),
            broker_connected=broker_connected,
            paper_trading=config.broker.paper_trading,
            dry_run=config.trading.dry_run,
            auto_trading=config.trading.auto_trading,
            last_update=datetime.now().isoformat()
        )
    else:
        return SystemStatus(
            status="config_error",
            broker_connected=False,
            paper_trading=True,
            dry_run=True,
            auto_trading=False,
            last_update=datetime.now().isoformat()
        )


@app.post("/api/initialize")
async def initialize_system(current_user: dict = Depends(get_current_user)):
    """시스템 초기화"""
    try:
        config = app_state["config"] = get_config()
        
        # 설정 검증
        validation = ConfigManager().validate_config(config)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail={
                "error": "설정 오류", 
                "details": validation["errors"]
            })
        
        # 브로커 연결
        broker = BrokerFactory.create_broker(
            broker_name=config.broker.name,
            api_key=config.broker.api_key,
            secret_key=config.broker.secret_key,
            paper_trading=config.broker.paper_trading,
            host=config.broker.host,
            port=config.broker.port
        )
        
        if not broker.authenticate():
            raise HTTPException(status_code=400, detail="브로커 인증 실패")
        
        app_state["broker"] = broker
        
        # 리스크 한도 설정
        risk_limits = RiskLimits(
            max_position_size=config.risk.max_position_size * 100000,
            max_total_exposure=config.risk.max_sector_exposure * 500000,
            max_daily_loss=config.risk.max_drawdown * 100000,
            min_confidence=config.risk.min_confidence
        )
        
        # 거래 엔진 초기화
        app_state["trading_engine"] = TradingEngine(
            broker=broker,
            risk_limits=risk_limits,
            dry_run=config.trading.dry_run
        )
        
        # 리스크 모니터 초기화
        app_state["risk_monitor"] = RiskMonitor(broker)
        
        app_state["system_status"] = "initialized"
        
        return {
            "success": True,
            "message": "시스템 초기화 완료",
            "warnings": validation.get("warnings", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시스템 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")


@app.get("/api/config")
async def get_config_api():
    """현재 설정 조회"""
    config = app_state.get("config")
    if not config:
        raise HTTPException(status_code=404, detail="설정이 로드되지 않았습니다")
    
    # API 키는 보안상 제외
    config_dict = {
        "broker": {
            "name": config.broker.name,
            "paper_trading": config.broker.paper_trading,
            "host": config.broker.host,
            "port": config.broker.port
        },
        "risk": {
            "max_position_size": config.risk.max_position_size,
            "max_sector_exposure": config.risk.max_sector_exposure,
            "min_confidence": config.risk.min_confidence,
            "max_drawdown": config.risk.max_drawdown
        },
        "trading": {
            "dry_run": config.trading.dry_run,
            "auto_trading": config.trading.auto_trading,
            "market_hours_only": config.trading.market_hours_only,
            "max_daily_trades": config.trading.max_daily_trades
        },
        "ai": {
            "model_name": config.ai.model_name,
            "model_provider": config.ai.model_provider,
            "selected_analysts": config.ai.selected_analysts
        }
    }
    
    return config_dict


@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """설정 업데이트"""
    config = app_state.get("config")
    if not config:
        raise HTTPException(status_code=404, detail="설정이 로드되지 않았습니다")
    
    try:
        # 설정 업데이트
        section = getattr(config, update.section)
        setattr(section, update.key, update.value)
        
        # 저장
        save_config(config)
        app_state["config"] = config
        
        return {"success": True, "message": "설정 업데이트 완료"}
        
    except AttributeError:
        raise HTTPException(status_code=400, detail="잘못된 설정 섹션 또는 키")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 업데이트 실패: {str(e)}")


@app.post("/api/analyze")
async def run_analysis(request: TradingRequest):
    """AI 분석 실행"""
    if not app_state.get("trading_engine"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    try:
        # 날짜 설정
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # 포트폴리오 초기화
        portfolio = {
            "cash": 100000.0,
            "margin_requirement": 0.0,
            "margin_used": 0.0,
            "positions": {
                ticker: {
                    "long": 0, "short": 0, 
                    "long_cost_basis": 0.0, "short_cost_basis": 0.0, 
                    "short_margin_used": 0.0
                } 
                for ticker in request.tickers
            },
            "realized_gains": {
                ticker: {"long": 0.0, "short": 0.0} 
                for ticker in request.tickers
            }
        }
        
        config = app_state["config"]
        
        # AI 분석 실행
        result = run_hedge_fund(
            tickers=request.tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            show_reasoning=config.ai.show_reasoning,
            selected_analysts=config.ai.selected_analysts or [],
            model_name=config.ai.model_name,
            model_provider=config.ai.model_provider
        )
        
        # 결과 저장
        app_state["last_analysis"] = {
            "timestamp": datetime.now().isoformat(),
            "tickers": request.tickers,
            "result": result
        }
        
        return result
        
    except Exception as e:
        logger.error(f"AI 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@app.post("/api/execute")
async def execute_trades(current_user: dict = Depends(get_current_user)):
    """거래 실행"""
    if not app_state.get("trading_engine"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    last_analysis = app_state.get("last_analysis")
    if not last_analysis or "decisions" not in last_analysis["result"]:
        raise HTTPException(status_code=400, detail="실행할 분석 결과가 없습니다")
    
    try:
        # 리스크 체크
        risk_check = app_state["risk_monitor"].run_risk_check()
        if risk_check["status"] == "EMERGENCY":
            raise HTTPException(status_code=400, detail={
                "error": "긴급 상황으로 인한 거래 중단",
                "risk_status": risk_check
            })
        
        # 거래 실행
        execution_results = app_state["trading_engine"].execute_signals(
            last_analysis["result"]["decisions"]
        )
        
        # 거래 기록 저장
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "analysis": last_analysis,
            "execution_results": execution_results,
            "risk_status": risk_check
        }
        app_state["trading_history"].append(trade_record)
        
        return {
            "execution_results": execution_results,
            "risk_status": risk_check
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=f"거래 실행 실패: {str(e)}")


@app.get("/api/account")
async def get_account():
    """계좌 정보 조회"""
    if not app_state.get("trading_engine"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    try:
        account_summary = app_state["trading_engine"].get_account_summary()
        return account_summary
    except Exception as e:
        logger.error(f"계좌 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"계좌 조회 실패: {str(e)}")


@app.get("/api/risk")
async def get_risk_check():
    """리스크 체크"""
    if not app_state.get("risk_monitor"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    try:
        risk_result = app_state["risk_monitor"].run_risk_check()
        return risk_result
    except Exception as e:
        logger.error(f"리스크 체크 실패: {e}")
        raise HTTPException(status_code=500, detail=f"리스크 체크 실패: {str(e)}")


@app.post("/api/emergency-stop")
async def emergency_stop(current_user: dict = Depends(get_current_user)):
    """긴급 정지"""
    if not app_state.get("risk_monitor"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    try:
        result = app_state["risk_monitor"].emergency_stop()
        app_state["system_status"] = "emergency_stopped"
        return result
    except Exception as e:
        logger.error(f"긴급 정지 실패: {e}")
        raise HTTPException(status_code=500, detail=f"긴급 정지 실패: {str(e)}")


@app.get("/api/history")
async def get_trading_history(limit: int = 50):
    """거래 기록 조회"""
    history = app_state.get("trading_history", [])
    return history[-limit:] if history else []


@app.get("/api/last-analysis")
async def get_last_analysis():
    """마지막 분석 결과 조회"""
    last_analysis = app_state.get("last_analysis")
    if not last_analysis:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다")
    return last_analysis


# 연속 거래 백그라운드 태스크
continuous_trading_task = None

@app.post("/api/start-continuous")
async def start_continuous_trading(request: TradingRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """연속 거래 시작"""
    global continuous_trading_task
    
    if continuous_trading_task and not continuous_trading_task.done():
        raise HTTPException(status_code=400, detail="이미 연속 거래가 실행 중입니다")
    
    if not app_state.get("trading_engine"):
        raise HTTPException(status_code=400, detail="시스템이 초기화되지 않았습니다")
    
    async def continuous_trading():
        iteration = 0
        app_state["system_status"] = "continuous_trading"
        
        try:
            while True:
                iteration += 1
                logger.info(f"연속 거래 반복 {iteration} 시작")
                
                # 시장 개장 여부 확인
                config = app_state["config"]
                if config.trading.market_hours_only and not app_state["broker"].is_market_open():
                    logger.info("시장이 닫혀있어 대기 중")
                    await asyncio.sleep(request.interval_minutes * 60)
                    continue
                
                # AI 분석 실행 (별도 함수로 분리)
                await run_analysis(request)
                
                # 자동 거래가 활성화된 경우 거래 실행
                if config.trading.auto_trading:
                    await execute_trades()
                
                # 대기
                await asyncio.sleep(request.interval_minutes * 60)
                
        except asyncio.CancelledError:
            logger.info("연속 거래가 사용자에 의해 중단되었습니다")
            app_state["system_status"] = "stopped"
        except Exception as e:
            logger.error(f"연속 거래 중 오류: {e}")
            app_state["system_status"] = "error"
    
    continuous_trading_task = asyncio.create_task(continuous_trading())
    background_tasks.add_task(lambda: None)  # 태스크 등록
    
    return {"success": True, "message": "연속 거래가 시작되었습니다"}


@app.post("/api/stop-continuous")
async def stop_continuous_trading(current_user: dict = Depends(get_current_user)):
    """연속 거래 중단"""
    global continuous_trading_task
    
    if continuous_trading_task and not continuous_trading_task.done():
        continuous_trading_task.cancel()
        app_state["system_status"] = "stopped"
        return {"success": True, "message": "연속 거래가 중단되었습니다"}
    else:
        raise HTTPException(status_code=400, detail="실행 중인 연속 거래가 없습니다")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """웹소켓 엔드포인트"""
    await manager.connect(websocket)
    
    # 실시간 모니터링 시작
    global real_time_monitor
    if not real_time_monitor:
        real_time_monitor = RealTimeMonitor(app_state)
        await real_time_monitor.start_monitoring()
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "잘못된 JSON 형식입니다"
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/websocket-stats")
async def get_websocket_stats():
    """웹소켓 연결 통계"""
    return manager.get_stats()


@app.get("/api/economic-indicators")
async def get_economic_indicators_api(country: Optional[str] = None):
    """경제지표 조회
    
    Args:
        country: "US" 또는 "KR" (없으면 전체)
    """
    try:
        indicators = get_economic_indicators(country)
        return {
            "success": True,
            "count": len(indicators),
            "indicators": [ind.model_dump() for ind in indicators]
        }
    except Exception as e:
        logger.error(f"경제지표 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"경제지표 조회 실패: {str(e)}")


@app.get("/api/market-condition")
async def get_market_condition_api():
    """시장 상황 분석"""
    try:
        condition = get_market_condition()
        return {
            "success": True,
            "condition": condition.model_dump()
        }
    except Exception as e:
        logger.error(f"시장 상황 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시장 상황 분석 실패: {str(e)}")


@app.get("/api/news")
async def get_news_api(
    categories: Optional[str] = None,
    days: int = 7,
    limit: int = 50
):
    """최근 뉴스 조회
    
    Args:
        categories: 쉼표로 구분된 카테고리 (예: "미국경제,한국경제")
        days: 최근 며칠간의 뉴스
        limit: 최대 뉴스 개수
    """
    try:
        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",")]
        
        news_list = get_recent_news(category_list, days, limit)
        sentiment = analyze_news_sentiment(news_list)
        
        return {
            "success": True,
            "count": len(news_list),
            "news": [news.model_dump() for news in news_list],
            "sentiment": sentiment
        }
    except Exception as e:
        logger.error(f"뉴스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"뉴스 조회 실패: {str(e)}")


@app.get("/api/macro-dashboard")
async def get_macro_dashboard():
    """거시경제 대시보드 데이터 통합 조회"""
    try:
        # 병렬로 데이터 수집
        us_indicators = get_economic_indicators("US")
        kr_indicators = get_economic_indicators("KR")
        market_condition = get_market_condition()
        recent_news = get_recent_news(days=3, limit=20)
        news_sentiment = analyze_news_sentiment(recent_news)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "market_condition": market_condition.model_dump(),
            "indicators": {
                "us": [ind.model_dump() for ind in us_indicators],
                "kr": [ind.model_dump() for ind in kr_indicators]
            },
            "news": {
                "articles": [news.model_dump() for news in recent_news[:10]],
                "sentiment": news_sentiment
            }
        }
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")


# ============================================================================
# IQC 전략 API 엔드포인트
# ============================================================================

# IQC Request Models
class IQCRegimeRequest(BaseModel):
    interest_rate: float = Field(..., description="금리 (%)")
    gdp_growth: float = Field(..., description="GDP 성장률 (%)")
    unemployment_rate: float = Field(..., description="실업률 (%)")
    inflation_rate: float = Field(..., description="인플레이션율 (%)")
    pmi: Optional[float] = Field(None, description="PMI 지수")
    credit_spread: Optional[float] = Field(None, description="신용 스프레드 (bp)")


class IQCPortfolioRequest(BaseModel):
    tickers: List[str] = Field(..., description="종목 코드 리스트")
    total_capital: float = Field(default=1_000_000.0, description="총 운용 자본 ($)")
    num_long: int = Field(default=20, description="롱 포지션 종목 수")
    num_short: int = Field(default=20, description="숏 포지션 종목 수")
    regime_request: Optional[IQCRegimeRequest] = None


class IQCBacktestRequest(BaseModel):
    tickers: List[str] = Field(..., description="종목 코드 리스트")
    start_date: str = Field(..., description="시작일 (YYYY-MM-DD)")
    end_date: str = Field(..., description="종료일 (YYYY-MM-DD)")
    initial_capital: float = Field(default=1_000_000.0, description="초기 자본 ($)")
    rebalance_frequency: str = Field(default="MONTHLY", description="리밸런싱 주기 (MONTHLY/QUARTERLY/YEARLY)")


@app.post("/api/iqc/regime-analysis")
async def iqc_regime_analysis(request: IQCRegimeRequest):
    """IQC 전략: 시장 레짐 분석"""
    try:
        from src.quant.regime_detector import detect_current_regime

        result = detect_current_regime(
            interest_rate=request.interest_rate,
            gdp_growth=request.gdp_growth,
            unemployment_rate=request.unemployment_rate,
            inflation_rate=request.inflation_rate,
            pmi=request.pmi,
            credit_spread=request.credit_spread
        )

        return {
            "success": True,
            "regime": result.regime.value,
            "confidence": result.confidence,
            "rate_environment": result.rate_environment,
            "economic_cycle": result.economic_cycle,
            "recommended_sectors": result.recommended_sectors,
            "recommended_factors": result.recommended_factors,
            "reasoning": result.reasoning,
            "timestamp": result.timestamp
        }

    except Exception as e:
        logger.error(f"레짐 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"레짐 분석 실패: {str(e)}")


@app.post("/api/iqc/portfolio")
async def iqc_portfolio_generation(request: IQCPortfolioRequest):
    """IQC 전략: 롱-숏 포트폴리오 생성"""
    try:
        from src.quant.regime_detector import detect_current_regime
        from src.quant.alpha_factors import AlphaFactorCalculator, StockData
        from src.quant.portfolio_optimizer import LongShortOptimizer
        import numpy as np

        # 1. 레짐 분석
        if request.regime_request:
            regime_analysis = detect_current_regime(**request.regime_request.model_dump())
        else:
            # 기본 경제 지표 사용
            regime_analysis = detect_current_regime(
                interest_rate=5.5,
                gdp_growth=2.1,
                unemployment_rate=3.7,
                inflation_rate=3.1,
                pmi=51.0
            )

        # 2. 주식 데이터 수집 및 알파 팩터 계산 (샘플 데이터)
        calculator = AlphaFactorCalculator()
        stocks = []

        for ticker in request.tickers[:30]:  # 최대 30개 종목
            try:
                # 샘플 데이터 생성 (실제로는 Yahoo Finance API 사용)
                stock_data = StockData(
                    symbol=ticker,
                    current_price=100.0 + np.random.uniform(-50, 50),
                    market_cap=1_000_000_000 + np.random.uniform(0, 10_000_000_000),
                    price_1m_ago=95.0 + np.random.uniform(-10, 10),
                    price_3m_ago=90.0 + np.random.uniform(-10, 10),
                    price_6m_ago=85.0 + np.random.uniform(-10, 10),
                    price_1y_ago=80.0 + np.random.uniform(-10, 10),
                    pe_ratio=20.0 + np.random.uniform(-10, 10),
                    pb_ratio=3.0 + np.random.uniform(-1, 2),
                    dividend_yield=2.0 + np.random.uniform(0, 3),
                    roe=0.15 + np.random.uniform(-0.05, 0.1),
                    roa=0.08 + np.random.uniform(-0.03, 0.05),
                    debt_to_equity=0.5 + np.random.uniform(-0.2, 0.5),
                    earnings_growth=0.10 + np.random.uniform(-0.05, 0.15),
                    volatility_1m=0.20 + np.random.uniform(-0.05, 0.1),
                    news_sentiment=np.random.uniform(-0.5, 0.5)
                )

                factors = calculator.calculate_all_factors(stock_data)
                stocks.append((stock_data, factors))

            except Exception as e:
                logger.warning(f"{ticker} 데이터 생성 실패: {e}")
                continue

        if not stocks:
            raise HTTPException(status_code=400, detail="유효한 주식 데이터가 없습니다")

        # 3. 포트폴리오 최적화
        optimizer = LongShortOptimizer(
            num_long=request.num_long,
            num_short=request.num_short
        )

        portfolio = optimizer.optimize_portfolio(
            stocks=stocks,
            regime_analysis=regime_analysis,
            total_capital=request.total_capital
        )

        # 4. 리스크 평가
        from src.quant.risk_manager import RiskManager
        risk_manager = RiskManager()
        risk_assessment = risk_manager.assess_risk(portfolio)

        return {
            "success": True,
            "portfolio": {
                "regime": portfolio.regime.value,
                "regime_confidence": portfolio.regime_confidence,
                "long_positions": [p.model_dump() for p in portfolio.long_positions],
                "short_positions": [p.model_dump() for p in portfolio.short_positions],
                "total_long_exposure": portfolio.total_long_exposure,
                "total_short_exposure": portfolio.total_short_exposure,
                "net_exposure": portfolio.net_exposure,
                "gross_exposure": portfolio.gross_exposure,
                "expected_return": portfolio.expected_return,
                "expected_volatility": portfolio.expected_volatility,
                "sharpe_ratio": portfolio.sharpe_ratio
            },
            "risk_assessment": {
                "is_acceptable": risk_assessment.is_acceptable,
                "overall_risk_level": risk_assessment.overall_risk_level.value,
                "metrics": risk_assessment.metrics.model_dump(),
                "violations": [v.model_dump() for v in risk_assessment.violations],
                "recommendations": risk_assessment.recommendations
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포트폴리오 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 생성 실패: {str(e)}")


@app.post("/api/iqc/backtest")
async def iqc_backtest(request: IQCBacktestRequest):
    """IQC 전략: 백테스트 실행"""
    try:
        from src.quant.iqc_backtester import IQCBacktester, BacktestConfig, RebalanceFrequency

        # 백테스트 설정
        config = BacktestConfig(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            rebalance_frequency=RebalanceFrequency[request.rebalance_frequency]
        )

        # 백테스터 생성
        backtester = IQCBacktester(config)

        # 샘플 데이터 생성 (실제로는 실시간 데이터 사용)
        # TODO: 실제 시장 데이터로 교체 필요
        import numpy as np
        from datetime import datetime as dt, timedelta as td

        market_data = {}
        for ticker in request.tickers:
            prices = []
            current_price = 100.0
            current_date = dt.strptime(request.start_date, "%Y-%m-%d")
            end_date = dt.strptime(request.end_date, "%Y-%m-%d")

            while current_date <= end_date:
                change = np.random.uniform(-0.02, 0.02)
                current_price *= (1 + change)
                prices.append((current_date.strftime("%Y-%m-%d"), current_price))
                current_date += td(days=1)

            market_data[ticker] = prices

        # 레짐 데이터 (월별)
        from src.quant.regime_detector import RegimeSignals
        regime_data = [
            (request.start_date, RegimeSignals(
                interest_rate=5.5,
                gdp_growth=2.1,
                unemployment_rate=3.7,
                inflation_rate=3.1,
                pmi=51.0
            ))
        ]

        # 백테스트 실행
        result = backtester.run_backtest(
            stock_universe=request.tickers,
            market_data=market_data,
            regime_data=regime_data
        )

        return {
            "success": True,
            "total_return": result.total_return,
            "annualized_return": result.annualized_return,
            "volatility": result.volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown": result.max_drawdown,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_commission": result.total_commission,
            "total_slippage": result.total_slippage,
            "daily_performance": [p.model_dump() for p in result.daily_performance[-30:]],  # 최근 30일
            "timestamp": result.timestamp
        }

    except Exception as e:
        logger.error(f"백테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"백테스트 실패: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "src.web_api:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        log_level="info"
    )