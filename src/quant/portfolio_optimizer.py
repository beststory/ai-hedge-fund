"""
롱-숏 포트폴리오 최적화 엔진 (Long-Short Portfolio Optimizer)

IQC 우승 전략의 핵심 컴포넌트:
- 알파 팩터 점수를 기반으로 롱/숏 포지션 구성
- 시장 중립성 유지 (Dollar-Neutral)
- 레짐에 따른 팩터 가중치 조정
- 리스크 제약 조건 적용
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from src.quant.regime_detector import MarketRegime, RegimeAnalysis
from src.quant.alpha_factors import AlphaFactors, StockData

logger = logging.getLogger(__name__)


class PositionType(str, Enum):
    """포지션 타입"""
    LONG = "LONG"  # 매수 포지션
    SHORT = "SHORT"  # 매도 포지션


class PortfolioPosition(BaseModel):
    """개별 포지션 정보"""
    symbol: str = Field(..., description="종목 코드")
    position_type: PositionType = Field(..., description="포지션 타입 (LONG/SHORT)")
    alpha_score: float = Field(..., description="알파 팩터 종합 점수")
    weight: float = Field(..., description="포트폴리오 내 비중 (%)")
    allocation: float = Field(..., description="배정 금액 ($)")

    # 참고 정보
    current_price: float = Field(..., description="현재가")
    shares: int = Field(..., description="주식 수")
    expected_return: float = Field(default=0.0, description="예상 수익률 (%)")
    risk_score: float = Field(default=0.5, description="리스크 점수 (0-1)")


class PortfolioRecommendation(BaseModel):
    """포트폴리오 추천 결과"""
    regime: MarketRegime = Field(..., description="현재 시장 레짐")
    regime_confidence: float = Field(..., description="레짐 확신도")

    # 포지션
    long_positions: List[PortfolioPosition] = Field(default_factory=list, description="롱 포지션 목록")
    short_positions: List[PortfolioPosition] = Field(default_factory=list, description="숏 포지션 목록")

    # 포트폴리오 통계
    total_long_exposure: float = Field(..., description="총 롱 노출")
    total_short_exposure: float = Field(..., description="총 숏 노출")
    net_exposure: float = Field(..., description="순 노출 (롱 - 숏)")
    gross_exposure: float = Field(..., description="총 노출 (롱 + 숏)")

    # 예상 성과
    expected_return: float = Field(default=0.0, description="예상 수익률 (%)")
    expected_volatility: float = Field(default=0.0, description="예상 변동성 (%)")
    sharpe_ratio: float = Field(default=0.0, description="예상 샤프 비율")

    # 메타데이터
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    rebalancing_date: Optional[str] = None


class LongShortOptimizer:
    """롱-숏 포트폴리오 최적화기"""

    def __init__(
        self,
        num_long: int = 20,
        num_short: int = 20,
        max_position_size: float = 0.10,  # 최대 포지션 크기 10%
        target_net_exposure: float = 0.0,  # 시장 중립 목표
        target_gross_exposure: float = 2.0,  # 총 노출 200% (롱 100% + 숏 100%)
    ):
        """
        Args:
            num_long: 롱 포지션 종목 수
            num_short: 숏 포지션 종목 수
            max_position_size: 개별 포지션 최대 크기 (포트폴리오 대비 %)
            target_net_exposure: 목표 순 노출 (0 = 시장 중립)
            target_gross_exposure: 목표 총 노출 (2.0 = 롱 100% + 숏 100%)
        """
        self.num_long = num_long
        self.num_short = num_short
        self.max_position_size = max_position_size
        self.target_net_exposure = target_net_exposure
        self.target_gross_exposure = target_gross_exposure

        self.logger = logging.getLogger(__name__)

    def optimize_portfolio(
        self,
        stocks: List[Tuple[StockData, AlphaFactors]],
        regime_analysis: RegimeAnalysis,
        total_capital: float = 1_000_000.0
    ) -> PortfolioRecommendation:
        """
        포트폴리오 최적화 실행

        Args:
            stocks: (StockData, AlphaFactors) 튜플 리스트
            regime_analysis: 현재 시장 레짐 분석 결과
            total_capital: 총 운용 자본 ($)

        Returns:
            포트폴리오 추천 결과
        """
        try:
            self.logger.info("🎯 롱-숏 포트폴리오 최적화 시작...")
            self.logger.info(f"   총 자본: ${total_capital:,.0f}")
            self.logger.info(f"   현재 레짐: {regime_analysis.regime.value}")
            self.logger.info(f"   종목 수: {len(stocks)}개")

            # 1. 레짐에 따른 알파 팩터 가중치 조정
            adjusted_scores = self._adjust_factor_weights(stocks, regime_analysis)

            # 2. 주식 순위 매기기 (알파 점수 기준)
            ranked_stocks = sorted(
                adjusted_scores,
                key=lambda x: x[2],  # adjusted_alpha_score
                reverse=True
            )

            # 3. 롱/숏 포지션 선정
            long_candidates = ranked_stocks[:self.num_long]
            short_candidates = ranked_stocks[-self.num_short:]

            self.logger.info(f"   롱 포지션: {len(long_candidates)}개, 숏 포지션: {len(short_candidates)}개")

            # 4. 포지션 크기 계산
            long_positions = self._calculate_positions(
                long_candidates,
                PositionType.LONG,
                total_capital,
                regime_analysis
            )

            short_positions = self._calculate_positions(
                short_candidates,
                PositionType.SHORT,
                total_capital,
                regime_analysis
            )

            # 5. 포트폴리오 통계 계산
            total_long = sum(p.allocation for p in long_positions)
            total_short = sum(p.allocation for p in short_positions)
            net_exposure = total_long - total_short
            gross_exposure = total_long + total_short

            # 6. 예상 성과 계산
            expected_return = self._estimate_return(long_positions, short_positions)
            expected_volatility = self._estimate_volatility(long_positions, short_positions)
            sharpe_ratio = expected_return / expected_volatility if expected_volatility > 0 else 0.0

            result = PortfolioRecommendation(
                regime=regime_analysis.regime,
                regime_confidence=regime_analysis.confidence,
                long_positions=long_positions,
                short_positions=short_positions,
                total_long_exposure=total_long,
                total_short_exposure=total_short,
                net_exposure=net_exposure,
                gross_exposure=gross_exposure,
                expected_return=expected_return,
                expected_volatility=expected_volatility,
                sharpe_ratio=sharpe_ratio
            )

            self.logger.info("✅ 포트폴리오 최적화 완료")
            self.logger.info(f"   롱 노출: ${total_long:,.0f}")
            self.logger.info(f"   숏 노출: ${total_short:,.0f}")
            self.logger.info(f"   순 노출: ${net_exposure:,.0f} ({net_exposure/total_capital*100:.1f}%)")
            self.logger.info(f"   예상 수익률: {expected_return:.2f}%")
            self.logger.info(f"   예상 샤프: {sharpe_ratio:.2f}")

            return result

        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 최적화 실패: {e}")
            raise

    def _adjust_factor_weights(
        self,
        stocks: List[Tuple[StockData, AlphaFactors]],
        regime_analysis: RegimeAnalysis
    ) -> List[Tuple[StockData, AlphaFactors, float]]:
        """
        레짐에 따라 알파 팩터 가중치 조정

        Returns:
            (StockData, AlphaFactors, adjusted_alpha_score) 튜플 리스트
        """
        regime = regime_analysis.regime
        recommended_factors = regime_analysis.recommended_factors

        # 레짐별 팩터 가중치 매핑
        regime_weights = {
            MarketRegime.LOW_RATE_EXPANSION: {
                "모멘텀": 0.35,  # 성장주 장세에서 모멘텀 중시
                "성장": 0.25,
                "퀄리티": 0.20,
                "저변동성": 0.20
            },
            MarketRegime.LOW_RATE_RECESSION: {
                "가치": 0.30,  # 침체기에 가치주 선호
                "배당": 0.25,
                "저변동성": 0.25,
                "퀄리티": 0.20
            },
            MarketRegime.HIGH_RATE_EXPANSION: {
                "가치": 0.30,  # 고금리 확장기에 가치주 유리
                "배당": 0.25,
                "퀄리티": 0.25,
                "사이즈": 0.20
            },
            MarketRegime.HIGH_RATE_RECESSION: {
                "저변동성": 0.35,  # 고금리 침체기에 안전 자산 선호
                "퀄리티": 0.30,
                "가치": 0.20,
                "배당": 0.15
            }
        }

        weights = regime_weights.get(regime, {
            "모멘텀": 0.25,
            "가치": 0.25,
            "퀄리티": 0.25,
            "저변동성": 0.25
        })

        adjusted_stocks = []

        for stock_data, alpha_factors in stocks:
            # 기본 알파 점수
            base_score = alpha_factors.total_score

            # 레짐 조정 점수 계산
            adjusted_score = 0.0

            # 각 팩터 카테고리의 평균 점수 계산
            momentum_avg = (
                alpha_factors.momentum_1m + alpha_factors.momentum_3m +
                alpha_factors.momentum_6m + alpha_factors.momentum_12m
            ) / 4.0

            value_avg = (
                alpha_factors.value_pe + alpha_factors.value_pb +
                alpha_factors.value_ps + alpha_factors.value_dividend
            ) / 4.0

            quality_avg = (
                alpha_factors.quality_roe + alpha_factors.quality_roa +
                alpha_factors.quality_debt + alpha_factors.quality_growth
            ) / 4.0

            low_vol_avg = (
                alpha_factors.low_vol_1m + alpha_factors.low_vol_3m +
                alpha_factors.low_vol_1y
            ) / 3.0

            # 레짐 가중치 적용
            adjusted_score = (
                momentum_avg * weights.get("모멘텀", 0.25) +
                value_avg * weights.get("가치", 0.25) +
                quality_avg * weights.get("퀄리티", 0.25) +
                low_vol_avg * weights.get("저변동성", 0.25)
            )

            # 감성 점수 추가 (소량)
            adjusted_score += alpha_factors.sentiment_score * 0.05

            adjusted_stocks.append((stock_data, alpha_factors, adjusted_score))

        return adjusted_stocks

    def _calculate_positions(
        self,
        candidates: List[Tuple[StockData, AlphaFactors, float]],
        position_type: PositionType,
        total_capital: float,
        regime_analysis: RegimeAnalysis
    ) -> List[PortfolioPosition]:
        """
        포지션 크기 계산

        Args:
            candidates: (StockData, AlphaFactors, adjusted_score) 튜플 리스트
            position_type: LONG or SHORT
            total_capital: 총 자본
            regime_analysis: 레짐 분석 결과

        Returns:
            포지션 목록
        """
        positions = []

        # 총 알파 점수 합계 (정규화용)
        total_alpha = sum(abs(score) for _, _, score in candidates)

        # 타겟 노출 금액 (롱/숏 각각 총 자본의 100%)
        target_exposure = total_capital * (self.target_gross_exposure / 2.0)

        for stock_data, alpha_factors, alpha_score in candidates:
            # 정규화된 가중치 계산
            normalized_weight = abs(alpha_score) / total_alpha if total_alpha > 0 else 1.0 / len(candidates)

            # 최대 포지션 크기 제약
            weight = min(normalized_weight, self.max_position_size)

            # 배정 금액
            allocation = target_exposure * weight

            # 주식 수 계산
            shares = int(allocation / stock_data.current_price)
            actual_allocation = shares * stock_data.current_price

            # 예상 수익률 (알파 점수 기반 추정)
            # 알파 점수가 높을수록 높은 수익 기대
            expected_return = alpha_score * 100.0  # 알파 점수를 % 수익률로 변환

            # 리스크 점수 계산 (변동성 기반)
            volatility = alpha_factors.low_vol_composite
            risk_score = 1.0 - volatility  # 낮은 변동성 = 낮은 리스크

            position = PortfolioPosition(
                symbol=stock_data.symbol,
                position_type=position_type,
                alpha_score=alpha_score,
                weight=weight * 100.0,  # % 변환
                allocation=actual_allocation,
                current_price=stock_data.current_price,
                shares=shares,
                expected_return=expected_return,
                risk_score=risk_score
            )

            positions.append(position)

        return positions

    def _estimate_return(
        self,
        long_positions: List[PortfolioPosition],
        short_positions: List[PortfolioPosition]
    ) -> float:
        """
        포트폴리오 예상 수익률 계산

        Returns:
            예상 수익률 (%)
        """
        total_allocation = sum(p.allocation for p in long_positions) + sum(p.allocation for p in short_positions)

        if total_allocation == 0:
            return 0.0

        # 가중 평균 수익률
        long_return = sum(p.expected_return * p.allocation for p in long_positions)
        short_return = sum(p.expected_return * p.allocation for p in short_positions)

        # 롱-숏 전략: 롱 수익 - 숏 손실
        portfolio_return = (long_return - short_return) / total_allocation

        return portfolio_return

    def _estimate_volatility(
        self,
        long_positions: List[PortfolioPosition],
        short_positions: List[PortfolioPosition]
    ) -> float:
        """
        포트폴리오 예상 변동성 계산

        Returns:
            예상 변동성 (%)
        """
        # 단순화된 변동성 추정
        # 실제로는 공분산 행렬을 사용해야 하지만, 여기서는 개별 리스크의 가중 평균 사용

        total_allocation = sum(p.allocation for p in long_positions) + sum(p.allocation for p in short_positions)

        if total_allocation == 0:
            return 0.0

        # 가중 평균 리스크
        total_risk = sum(p.risk_score * p.allocation for p in long_positions + short_positions)
        avg_risk = total_risk / total_allocation

        # 리스크 점수를 변동성 %로 변환 (0-1 → 0-50%)
        volatility = avg_risk * 50.0

        return volatility

    def rebalance_portfolio(
        self,
        current_portfolio: PortfolioRecommendation,
        new_portfolio: PortfolioRecommendation,
        rebalance_threshold: float = 0.05  # 5% 이상 차이날 때만 리밸런싱
    ) -> Dict[str, List[PortfolioPosition]]:
        """
        포트폴리오 리밸런싱

        Args:
            current_portfolio: 현재 포트폴리오
            new_portfolio: 새로운 목표 포트폴리오
            rebalance_threshold: 리밸런싱 임계값

        Returns:
            {
                "add": 추가할 포지션,
                "remove": 제거할 포지션,
                "adjust": 조정할 포지션
            }
        """
        # 현재 포지션 맵
        current_positions = {
            **{p.symbol: p for p in current_portfolio.long_positions},
            **{p.symbol: p for p in current_portfolio.short_positions}
        }

        # 새로운 포지션 맵
        new_positions = {
            **{p.symbol: p for p in new_portfolio.long_positions},
            **{p.symbol: p for p in new_portfolio.short_positions}
        }

        add_positions = []
        remove_positions = []
        adjust_positions = []

        # 추가할 포지션
        for symbol, new_pos in new_positions.items():
            if symbol not in current_positions:
                add_positions.append(new_pos)
            else:
                current_pos = current_positions[symbol]
                weight_diff = abs(new_pos.weight - current_pos.weight) / current_pos.weight

                if weight_diff > rebalance_threshold:
                    adjust_positions.append(new_pos)

        # 제거할 포지션
        for symbol, current_pos in current_positions.items():
            if symbol not in new_positions:
                remove_positions.append(current_pos)

        self.logger.info(f"📊 리밸런싱: 추가 {len(add_positions)}개, 제거 {len(remove_positions)}개, 조정 {len(adjust_positions)}개")

        return {
            "add": add_positions,
            "remove": remove_positions,
            "adjust": adjust_positions
        }


# 전역 인스턴스
_optimizer = None


def get_optimizer() -> LongShortOptimizer:
    """LongShortOptimizer 싱글톤 인스턴스 반환"""
    global _optimizer
    if _optimizer is None:
        _optimizer = LongShortOptimizer()
    return _optimizer


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)

    from src.quant.regime_detector import detect_current_regime
    from src.quant.alpha_factors import AlphaFactorCalculator

    print("=" * 80)
    print("롱-숏 포트폴리오 최적화 테스트")
    print("=" * 80)

    # 1. 현재 레짐 감지
    regime_analysis = detect_current_regime(
        interest_rate=5.5,
        gdp_growth=2.1,
        unemployment_rate=3.7,
        inflation_rate=3.1,
        pmi=51.0
    )

    print(f"\n현재 레짐: {regime_analysis.regime.value}")
    print(f"확신도: {regime_analysis.confidence:.2%}")
    print(f"추천 팩터: {', '.join(regime_analysis.recommended_factors)}")

    # 2. 샘플 주식 데이터 생성
    calculator = AlphaFactorCalculator()

    stocks = []

    # 고성장 기술주 (높은 알파)
    for i in range(5):
        stock = StockData(
            symbol=f"TECH{i}",
            current_price=150.0 + i * 10,
            market_cap=500_000_000_000,
            price_1m_ago=140.0,
            price_3m_ago=120.0,
            price_6m_ago=100.0,
            price_1y_ago=80.0,
            pe_ratio=35.0,
            pb_ratio=8.0,
            dividend_yield=0.5,
            roe=0.35,
            roa=0.20,
            debt_to_equity=0.3,
            earnings_growth=0.30,
            volatility_1m=0.25,
            news_sentiment=0.7
        )
        factors = calculator.calculate_all_factors(stock)
        stocks.append((stock, factors))

    # 가치주 (중간 알파)
    for i in range(5):
        stock = StockData(
            symbol=f"VALUE{i}",
            current_price=80.0 + i * 5,
            market_cap=100_000_000_000,
            price_1m_ago=78.0,
            price_3m_ago=75.0,
            price_6m_ago=72.0,
            price_1y_ago=70.0,
            pe_ratio=12.0,
            pb_ratio=1.5,
            dividend_yield=4.0,
            roe=0.15,
            roa=0.08,
            debt_to_equity=0.5,
            earnings_growth=0.05,
            volatility_1m=0.15,
            news_sentiment=0.3
        )
        factors = calculator.calculate_all_factors(stock)
        stocks.append((stock, factors))

    # 저성장 주식 (낮은 알파)
    for i in range(5):
        stock = StockData(
            symbol=f"SLOW{i}",
            current_price=50.0 + i * 2,
            market_cap=50_000_000_000,
            price_1m_ago=51.0,
            price_3m_ago=52.0,
            price_6m_ago=53.0,
            price_1y_ago=55.0,
            pe_ratio=25.0,
            pb_ratio=2.0,
            dividend_yield=1.0,
            roe=0.05,
            roa=0.02,
            debt_to_equity=1.2,
            earnings_growth=-0.05,
            volatility_1m=0.20,
            news_sentiment=-0.3
        )
        factors = calculator.calculate_all_factors(stock)
        stocks.append((stock, factors))

    # 3. 포트폴리오 최적화
    optimizer = LongShortOptimizer(
        num_long=5,
        num_short=5,
        max_position_size=0.15,
        target_gross_exposure=2.0
    )

    portfolio = optimizer.optimize_portfolio(
        stocks=stocks,
        regime_analysis=regime_analysis,
        total_capital=1_000_000.0
    )

    # 4. 결과 출력
    print("\n" + "=" * 80)
    print("📈 롱 포지션")
    print("=" * 80)
    print(f"{'종목':<10} {'가격':<10} {'주식수':<10} {'배정금액':<15} {'비중':<10} {'알파점수':<12}")
    print("-" * 80)

    for pos in portfolio.long_positions:
        print(f"{pos.symbol:<10} ${pos.current_price:<9.2f} {pos.shares:<10} ${pos.allocation:<14,.0f} {pos.weight:<9.2f}% {pos.alpha_score:<12.4f}")

    print(f"\n총 롱 노출: ${portfolio.total_long_exposure:,.0f}")

    print("\n" + "=" * 80)
    print("📉 숏 포지션")
    print("=" * 80)
    print(f"{'종목':<10} {'가격':<10} {'주식수':<10} {'배정금액':<15} {'비중':<10} {'알파점수':<12}")
    print("-" * 80)

    for pos in portfolio.short_positions:
        print(f"{pos.symbol:<10} ${pos.current_price:<9.2f} {pos.shares:<10} ${pos.allocation:<14,.0f} {pos.weight:<9.2f}% {pos.alpha_score:<12.4f}")

    print(f"\n총 숏 노출: ${portfolio.total_short_exposure:,.0f}")

    print("\n" + "=" * 80)
    print("📊 포트폴리오 통계")
    print("=" * 80)
    print(f"순 노출 (Net Exposure):     ${portfolio.net_exposure:,.0f} ({portfolio.net_exposure/1_000_000*100:.1f}%)")
    print(f"총 노출 (Gross Exposure):   ${portfolio.gross_exposure:,.0f} ({portfolio.gross_exposure/1_000_000*100:.1f}%)")
    print(f"예상 수익률:                {portfolio.expected_return:.2f}%")
    print(f"예상 변동성:                {portfolio.expected_volatility:.2f}%")
    print(f"예상 샤프 비율:             {portfolio.sharpe_ratio:.2f}")
    print("=" * 80)
