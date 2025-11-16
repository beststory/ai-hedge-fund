"""
IQC 전략 백테스팅 시스템 (IQC Strategy Backtester)

롱-숏 전략의 과거 성과 시뮬레이션:
- 레짐 기반 동적 팩터 가중치
- 월별/분기별 리밸런싱
- 거래 비용 및 슬리피지 반영
- 상세 성과 지표 계산
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import numpy as np

from src.quant.regime_detector import MarketRegime, RegimeSignals, detect_current_regime
from src.quant.alpha_factors import AlphaFactorCalculator, StockData, AlphaFactors
from src.quant.portfolio_optimizer import LongShortOptimizer, PortfolioRecommendation
from src.quant.risk_manager import RiskManager, RiskConstraints

logger = logging.getLogger(__name__)


class RebalanceFrequency(str, Enum):
    """리밸런싱 주기"""
    MONTHLY = "월별"
    QUARTERLY = "분기별"
    YEARLY = "연별"


class BacktestConfig(BaseModel):
    """백테스트 설정"""
    # 기간
    start_date: str = Field(..., description="시작일 (YYYY-MM-DD)")
    end_date: str = Field(..., description="종료일 (YYYY-MM-DD)")

    # 자본
    initial_capital: float = Field(default=1_000_000.0, description="초기 자본 ($)")

    # 리밸런싱
    rebalance_frequency: RebalanceFrequency = Field(default=RebalanceFrequency.MONTHLY, description="리밸런싱 주기")

    # 거래 비용
    commission_rate: float = Field(default=0.001, description="거래 수수료 (0.1%)")
    slippage_rate: float = Field(default=0.0005, description="슬리피지 (0.05%)")

    # 포트폴리오 설정
    num_long: int = Field(default=20, description="롱 포지션 수")
    num_short: int = Field(default=20, description="숏 포지션 수")

    # 리스크 제약
    risk_constraints: Optional[RiskConstraints] = None


class DailyPerformance(BaseModel):
    """일별 성과"""
    date: str = Field(..., description="날짜")
    portfolio_value: float = Field(..., description="포트폴리오 가치")
    daily_return: float = Field(..., description="일일 수익률 (%)")
    cumulative_return: float = Field(..., description="누적 수익률 (%)")
    regime: MarketRegime = Field(..., description="시장 레짐")


class BacktestResult(BaseModel):
    """백테스트 결과"""
    config: BacktestConfig = Field(..., description="백테스트 설정")

    # 전체 성과
    total_return: float = Field(..., description="총 수익률 (%)")
    annualized_return: float = Field(..., description="연환산 수익률 (%)")
    volatility: float = Field(..., description="변동성 (%)")
    sharpe_ratio: float = Field(..., description="샤프 비율")
    sortino_ratio: float = Field(..., description="소르티노 비율")
    max_drawdown: float = Field(..., description="최대 낙폭 (%)")

    # 거래 통계
    total_trades: int = Field(..., description="총 거래 횟수")
    winning_trades: int = Field(..., description="수익 거래 횟수")
    losing_trades: int = Field(..., description="손실 거래 횟수")
    win_rate: float = Field(..., description="승률 (%)")

    # 비용
    total_commission: float = Field(..., description="총 수수료")
    total_slippage: float = Field(..., description="총 슬리피지")

    # 일별 성과
    daily_performance: List[DailyPerformance] = Field(default_factory=list, description="일별 성과 기록")

    # 최종 포트폴리오
    final_portfolio: Optional[PortfolioRecommendation] = None

    # 메타데이터
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class IQCBacktester:
    """IQC 전략 백테스터"""

    def __init__(self, config: BacktestConfig):
        """
        Args:
            config: 백테스트 설정
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 컴포넌트 초기화
        self.alpha_calculator = AlphaFactorCalculator()
        self.optimizer = LongShortOptimizer(
            num_long=config.num_long,
            num_short=config.num_short
        )
        self.risk_manager = RiskManager(config.risk_constraints)

    def run_backtest(
        self,
        stock_universe: List[str],
        market_data: Dict[str, List[Tuple[str, float]]],  # {symbol: [(date, price), ...]}
        regime_data: List[Tuple[str, RegimeSignals]]  # [(date, signals), ...]
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            stock_universe: 주식 유니버스 (종목 코드 리스트)
            market_data: 시장 데이터 {종목: [(날짜, 가격), ...]}
            regime_data: 레짐 데이터 [(날짜, 레짐 시그널), ...]

        Returns:
            백테스트 결과
        """
        try:
            self.logger.info("🚀 IQC 전략 백테스트 시작...")
            self.logger.info(f"   기간: {self.config.start_date} ~ {self.config.end_date}")
            self.logger.info(f"   초기 자본: ${self.config.initial_capital:,.0f}")
            self.logger.info(f"   리밸런싱: {self.config.rebalance_frequency.value}")

            # 초기화
            current_capital = self.config.initial_capital
            current_portfolio = None
            daily_performance = []
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            total_commission = 0.0
            total_slippage = 0.0

            # 날짜 범위 생성
            start_date = datetime.strptime(self.config.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.config.end_date, "%Y-%m-%d")
            current_date = start_date

            # 리밸런싱 날짜 계산
            rebalance_dates = self._calculate_rebalance_dates(start_date, end_date)

            regime_idx = 0
            portfolio_values = []

            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")

                # 현재 레짐 가져오기
                current_regime_signals = self._get_regime_at_date(regime_data, date_str, regime_idx)
                if current_regime_signals:
                    regime_idx += 1

                current_regime = detect_current_regime(**current_regime_signals.model_dump()) if current_regime_signals else None

                # 리밸런싱 체크
                if date_str in rebalance_dates or current_portfolio is None:
                    self.logger.info(f"📅 {date_str}: 리밸런싱 실행")

                    # 주식 데이터 수집
                    stocks = self._collect_stock_data(stock_universe, market_data, date_str)

                    if stocks and current_regime:
                        # 포트폴리오 최적화
                        new_portfolio = self.optimizer.optimize_portfolio(
                            stocks=stocks,
                            regime_analysis=current_regime,
                            total_capital=current_capital
                        )

                        # 리스크 평가
                        risk_assessment = self.risk_manager.assess_risk(new_portfolio)

                        if not risk_assessment.is_acceptable:
                            self.logger.warning(f"⚠️ 리스크 한도 초과. 포지션 조정 중...")
                            new_portfolio = self.risk_manager.adjust_portfolio_for_risk(
                                new_portfolio,
                                risk_assessment
                            )

                        # 거래 비용 계산
                        if current_portfolio:
                            trade_cost = self._calculate_trade_cost(current_portfolio, new_portfolio)
                            total_commission += trade_cost["commission"]
                            total_slippage += trade_cost["slippage"]
                            total_trades += trade_cost["num_trades"]
                            current_capital -= (trade_cost["commission"] + trade_cost["slippage"])

                        current_portfolio = new_portfolio

                # 일일 성과 계산
                if current_portfolio:
                    daily_pnl = self._calculate_daily_pnl(current_portfolio, market_data, date_str)
                    current_capital += daily_pnl

                    # 수익 vs 손실 거래 집계
                    if daily_pnl > 0:
                        winning_trades += 1
                    elif daily_pnl < 0:
                        losing_trades += 1

                    # 일일 수익률
                    daily_return = (daily_pnl / current_capital) * 100 if current_capital > 0 else 0.0
                    cumulative_return = ((current_capital - self.config.initial_capital) / self.config.initial_capital) * 100

                    daily_perf = DailyPerformance(
                        date=date_str,
                        portfolio_value=current_capital,
                        daily_return=daily_return,
                        cumulative_return=cumulative_return,
                        regime=current_regime.regime if current_regime else MarketRegime.LOW_RATE_EXPANSION
                    )
                    daily_performance.append(daily_perf)
                    portfolio_values.append(current_capital)

                # 다음 날로 이동
                current_date += timedelta(days=1)

            # 최종 성과 지표 계산
            total_return = ((current_capital - self.config.initial_capital) / self.config.initial_capital) * 100

            # 연환산 수익률
            days = (end_date - start_date).days
            years = days / 365.0
            annualized_return = ((current_capital / self.config.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0

            # 변동성 (일일 수익률의 표준편차)
            daily_returns = [p.daily_return for p in daily_performance]
            volatility = np.std(daily_returns) * np.sqrt(252) if daily_returns else 0.0  # 연환산

            # 샤프 비율
            risk_free_rate = 2.0  # 무위험 수익률 2%
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0.0

            # 소르티노 비율 (하방 변동성만 고려)
            negative_returns = [r for r in daily_returns if r < 0]
            downside_volatility = np.std(negative_returns) * np.sqrt(252) if negative_returns else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0.0

            # 최대 낙폭 (MDD)
            max_drawdown = self._calculate_max_drawdown(portfolio_values)

            # 승률
            total_trade_count = winning_trades + losing_trades
            win_rate = (winning_trades / total_trade_count * 100) if total_trade_count > 0 else 0.0

            result = BacktestResult(
                config=self.config,
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_commission=total_commission,
                total_slippage=total_slippage,
                daily_performance=daily_performance,
                final_portfolio=current_portfolio
            )

            self.logger.info("✅ 백테스트 완료")
            self.logger.info(f"   총 수익률: {total_return:.2f}%")
            self.logger.info(f"   연환산 수익률: {annualized_return:.2f}%")
            self.logger.info(f"   샤프 비율: {sharpe_ratio:.2f}")
            self.logger.info(f"   최대 낙폭: {max_drawdown:.2f}%")
            self.logger.info(f"   승률: {win_rate:.2f}%")

            return result

        except Exception as e:
            self.logger.error(f"❌ 백테스트 실패: {e}")
            raise

    def _calculate_rebalance_dates(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[str]:
        """리밸런싱 날짜 계산"""

        dates = []
        current_date = start_date

        if self.config.rebalance_frequency == RebalanceFrequency.MONTHLY:
            # 매월 첫 영업일
            while current_date <= end_date:
                dates.append(current_date.strftime("%Y-%m-%d"))
                # 다음 달 1일로 이동
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1, day=1)

        elif self.config.rebalance_frequency == RebalanceFrequency.QUARTERLY:
            # 분기별 (1, 4, 7, 10월)
            while current_date <= end_date:
                if current_date.month in [1, 4, 7, 10]:
                    dates.append(current_date.strftime("%Y-%m-%d"))

                # 다음 분기로 이동
                next_quarter_month = ((current_date.month - 1) // 3 + 1) * 3 + 1
                if next_quarter_month > 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    current_date = current_date.replace(month=next_quarter_month, day=1)

        elif self.config.rebalance_frequency == RebalanceFrequency.YEARLY:
            # 연별 (매년 1월)
            while current_date <= end_date:
                if current_date.month == 1:
                    dates.append(current_date.strftime("%Y-%m-%d"))
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)

        return dates

    def _get_regime_at_date(
        self,
        regime_data: List[Tuple[str, RegimeSignals]],
        date_str: str,
        current_idx: int
    ) -> Optional[RegimeSignals]:
        """특정 날짜의 레짐 시그널 가져오기"""

        if current_idx < len(regime_data):
            _, signals = regime_data[current_idx]
            return signals
        return None

    def _collect_stock_data(
        self,
        stock_universe: List[str],
        market_data: Dict[str, List[Tuple[str, float]]],
        date_str: str
    ) -> List[Tuple[StockData, AlphaFactors]]:
        """특정 날짜의 주식 데이터 수집"""

        stocks = []

        for symbol in stock_universe:
            if symbol not in market_data:
                continue

            # 현재 가격 찾기
            prices = market_data[symbol]
            current_price = None

            for price_date, price in prices:
                if price_date == date_str:
                    current_price = price
                    break

            if current_price is None:
                continue

            # 과거 가격 찾기 (단순화를 위해 임의 생성)
            price_1m = current_price * 0.95
            price_3m = current_price * 0.90
            price_6m = current_price * 0.85
            price_1y = current_price * 0.80

            # StockData 생성 (실제로는 재무 데이터도 필요)
            stock_data = StockData(
                symbol=symbol,
                current_price=current_price,
                market_cap=100_000_000_000,  # 임의값
                price_1m_ago=price_1m,
                price_3m_ago=price_3m,
                price_6m_ago=price_6m,
                price_1y_ago=price_1y,
                pe_ratio=20.0,
                pb_ratio=3.0,
                dividend_yield=2.0,
                roe=0.15,
                roa=0.08,
                debt_to_equity=0.5,
                earnings_growth=0.10,
                volatility_1m=0.20,
                news_sentiment=0.5
            )

            # 알파 팩터 계산
            factors = self.alpha_calculator.calculate_all_factors(stock_data)

            stocks.append((stock_data, factors))

        return stocks

    def _calculate_trade_cost(
        self,
        old_portfolio: PortfolioRecommendation,
        new_portfolio: PortfolioRecommendation
    ) -> Dict[str, float]:
        """거래 비용 계산"""

        # 리밸런싱으로 인한 거래량 계산
        old_positions = {p.symbol: p for p in old_portfolio.long_positions + old_portfolio.short_positions}
        new_positions = {p.symbol: p for p in new_portfolio.long_positions + new_portfolio.short_positions}

        trade_volume = 0.0
        num_trades = 0

        # 추가/제거된 포지션
        for symbol in set(old_positions.keys()) | set(new_positions.keys()):
            old_alloc = old_positions.get(symbol).allocation if symbol in old_positions else 0.0
            new_alloc = new_positions.get(symbol).allocation if symbol in new_positions else 0.0
            trade_volume += abs(new_alloc - old_alloc)
            if old_alloc != new_alloc:
                num_trades += 1

        # 비용 계산
        commission = trade_volume * self.config.commission_rate
        slippage = trade_volume * self.config.slippage_rate

        return {
            "commission": commission,
            "slippage": slippage,
            "num_trades": num_trades,
            "trade_volume": trade_volume
        }

    def _calculate_daily_pnl(
        self,
        portfolio: PortfolioRecommendation,
        market_data: Dict[str, List[Tuple[str, float]]],
        date_str: str
    ) -> float:
        """일일 손익 계산"""

        total_pnl = 0.0

        # 롱 포지션 손익
        for pos in portfolio.long_positions:
            if pos.symbol in market_data:
                prices = market_data[pos.symbol]
                current_price = None
                prev_price = None

                for i, (price_date, price) in enumerate(prices):
                    if price_date == date_str:
                        current_price = price
                        if i > 0:
                            prev_price = prices[i - 1][1]
                        break

                if current_price and prev_price:
                    price_change = (current_price - prev_price) / prev_price
                    pnl = pos.allocation * price_change
                    total_pnl += pnl

        # 숏 포지션 손익 (가격 하락 시 수익)
        for pos in portfolio.short_positions:
            if pos.symbol in market_data:
                prices = market_data[pos.symbol]
                current_price = None
                prev_price = None

                for i, (price_date, price) in enumerate(prices):
                    if price_date == date_str:
                        current_price = price
                        if i > 0:
                            prev_price = prices[i - 1][1]
                        break

                if current_price and prev_price:
                    price_change = (current_price - prev_price) / prev_price
                    pnl = pos.allocation * (-price_change)  # 숏은 반대
                    total_pnl += pnl

        return total_pnl

    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """최대 낙폭 (MDD) 계산"""

        if not portfolio_values:
            return 0.0

        peak = portfolio_values[0]
        max_dd = 0.0

        for value in portfolio_values:
            if value > peak:
                peak = value

            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd


# 전역 인스턴스
_backtester = None


def get_backtester(config: BacktestConfig) -> IQCBacktester:
    """IQCBacktester 인스턴스 반환"""
    global _backtester
    if _backtester is None or _backtester.config != config:
        _backtester = IQCBacktester(config)
    return _backtester


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("IQC 전략 백테스팅 시스템 테스트")
    print("=" * 80)

    # 백테스트 설정
    config = BacktestConfig(
        start_date="2024-01-01",
        end_date="2024-03-31",
        initial_capital=1_000_000.0,
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        num_long=5,
        num_short=5
    )

    # 샘플 데이터 생성
    stock_universe = [f"STOCK{i}" for i in range(10)]

    # 시장 데이터 (간단한 랜덤 워크)
    market_data = {}
    for symbol in stock_universe:
        prices = []
        current_price = 100.0
        current_date = datetime.strptime(config.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(config.end_date, "%Y-%m-%d")

        while current_date <= end_date:
            # 랜덤 변동 (-2% ~ +2%)
            change = np.random.uniform(-0.02, 0.02)
            current_price *= (1 + change)
            prices.append((current_date.strftime("%Y-%m-%d"), current_price))
            current_date += timedelta(days=1)

        market_data[symbol] = prices

    # 레짐 데이터 (월별로 변경)
    regime_data = [
        ("2024-01-01", RegimeSignals(
            interest_rate=5.5,
            gdp_growth=2.1,
            unemployment_rate=3.7,
            inflation_rate=3.1,
            pmi=51.0
        )),
        ("2024-02-01", RegimeSignals(
            interest_rate=5.5,
            gdp_growth=2.3,
            unemployment_rate=3.6,
            inflation_rate=3.0,
            pmi=52.0
        )),
        ("2024-03-01", RegimeSignals(
            interest_rate=5.25,
            gdp_growth=2.5,
            unemployment_rate=3.5,
            inflation_rate=2.9,
            pmi=53.0
        ))
    ]

    # 백테스트 실행
    backtester = IQCBacktester(config)
    result = backtester.run_backtest(
        stock_universe=stock_universe,
        market_data=market_data,
        regime_data=regime_data
    )

    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 백테스트 결과")
    print("=" * 80)
    print(f"총 수익률:           {result.total_return:.2f}%")
    print(f"연환산 수익률:       {result.annualized_return:.2f}%")
    print(f"변동성:             {result.volatility:.2f}%")
    print(f"샤프 비율:          {result.sharpe_ratio:.2f}")
    print(f"소르티노 비율:       {result.sortino_ratio:.2f}")
    print(f"최대 낙폭:          {result.max_drawdown:.2f}%")
    print(f"\n총 거래 횟수:        {result.total_trades}회")
    print(f"수익 거래:          {result.winning_trades}회")
    print(f"손실 거래:          {result.losing_trades}회")
    print(f"승률:              {result.win_rate:.2f}%")
    print(f"\n총 수수료:          ${result.total_commission:,.2f}")
    print(f"총 슬리피지:        ${result.total_slippage:,.2f}")

    print("\n" + "=" * 80)
    print("📈 월별 성과")
    print("=" * 80)
    monthly_returns = {}
    for perf in result.daily_performance:
        month = perf.date[:7]  # YYYY-MM
        if month not in monthly_returns:
            monthly_returns[month] = []
        monthly_returns[month].append(perf.daily_return)

    for month, returns in sorted(monthly_returns.items()):
        monthly_return = sum(returns)
        print(f"{month}: {monthly_return:+.2f}%")

    print("=" * 80)
