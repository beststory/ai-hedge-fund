"""
IQC 전략 전용 웹서버 (간소화 버전)

WorldQuant IQC 우승 전략 API를 제공하는 경량 웹서버
"""
import logging
from typing import List, Optional
from datetime import datetime
import numpy as np
from datetime import datetime as dt, timedelta as td

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IQC 전략 API",
    description="WorldQuant International Quant Championship 우승 전략",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Models
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
    rebalance_frequency: str = Field(default="MONTHLY", description="리밸런싱 주기")


@app.get("/")
async def root():
    """API 정보"""
    return {
        "title": "IQC 전략 API",
        "description": "WorldQuant International Quant Championship 우승 전략",
        "version": "1.0.0",
        "endpoints": {
            "regime_analysis": "POST /api/iqc/regime-analysis",
            "portfolio": "POST /api/iqc/portfolio",
            "backtest": "POST /api/iqc/backtest"
        },
        "docs": "/docs"
    }


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
        from src.quant.regime_detector import detect_current_regime, RegimeSignals
        from src.quant.alpha_factors import AlphaFactorCalculator, StockData
        from src.quant.portfolio_optimizer import LongShortOptimizer

        # 1. 레짐 분석
        if request.regime_request:
            regime_analysis = detect_current_regime(**request.regime_request.model_dump())
        else:
            # 기본 경제 지표 사용 (샘플)
            regime_analysis = detect_current_regime(
                interest_rate=5.5,
                gdp_growth=2.1,
                unemployment_rate=3.7,
                inflation_rate=3.1,
                pmi=51.0
            )

        # 2. 주식 데이터 수집 및 알파 팩터 계산 (간소화)
        calculator = AlphaFactorCalculator()
        stocks = []

        for ticker in request.tickers[:30]:  # 최대 30개 종목
            try:
                # 샘플 데이터 (실제로는 Yahoo Finance API 사용)
                stock_data = StockData(
                    symbol=ticker,
                    current_price=100.0 + np.random.uniform(-50, 50),
                    market_cap=1_000_000_000 + np.random.uniform(0, 10_000_000_000),
                    price_1m_ago=95.0,
                    price_3m_ago=90.0,
                    price_6m_ago=85.0,
                    price_1y_ago=80.0,
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
            num_long=min(request.num_long, len(stocks) // 2),
            num_short=min(request.num_short, len(stocks) // 2)
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
        from src.quant.regime_detector import RegimeSignals

        # 백테스트 설정
        config = BacktestConfig(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            rebalance_frequency=RebalanceFrequency[request.rebalance_frequency]
        )

        # 백테스터 생성
        backtester = IQCBacktester(config)

        # 샘플 데이터 생성
        market_data = {}
        for ticker in request.tickers[:10]:  # 최대 10개 종목
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

        # 레짐 데이터
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
            stock_universe=request.tickers[:10],
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
            "daily_performance": [p.model_dump() for p in result.daily_performance[-30:]],
            "timestamp": result.timestamp
        }

    except Exception as e:
        logger.error(f"백테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"백테스트 실패: {str(e)}")


if __name__ == "__main__":
    print("=" * 80)
    print("🚀 IQC 전략 웹서버 시작")
    print("=" * 80)
    print(f"서버 주소: http://192.168.1.3:9999")
    print(f"API 문서: http://192.168.1.3:9999/docs")
    print(f"")
    print(f"사용 가능한 엔드포인트:")
    print(f"  - POST /api/iqc/regime-analysis    # 시장 레짐 분석")
    print(f"  - POST /api/iqc/portfolio          # 롱-숏 포트폴리오 생성")
    print(f"  - POST /api/iqc/backtest           # 백테스트 실행")
    print("=" * 80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9999,
        log_level="info"
    )
