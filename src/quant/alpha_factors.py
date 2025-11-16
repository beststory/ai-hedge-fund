"""
알파 팩터 계산 모듈

IQC 우승 전략에서 사용된 32개 정량 팩터를 구현합니다.

팩터 카테고리:
1. 모멘텀 (Momentum) - 7개
2. 가치 (Value) - 6개
3. 퀄리티 (Quality) - 6개
4. 저변동성 (Low Volatility) - 4개
5. 사이즈 (Size) - 3개
6. 리스크 스프레드 (Risk Spread) - 3개
7. 뉴스/감성 (Sentiment) - 2개
8. 변동성 스프레드 (Volatility Spread) - 1개

총 32개 알파 팩터
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StockData(BaseModel):
    """개별 종목 데이터"""
    symbol: str
    current_price: float
    market_cap: Optional[float] = None

    # 가격 데이터
    price_1m_ago: Optional[float] = None
    price_3m_ago: Optional[float] = None
    price_6m_ago: Optional[float] = None
    price_1y_ago: Optional[float] = None

    # 재무 데이터
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    pcf_ratio: Optional[float] = None  # Price to Cash Flow
    dividend_yield: Optional[float] = None

    # 퀄리티 지표
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    earnings_growth: Optional[float] = None
    revenue_growth: Optional[float] = None

    # 변동성
    volatility_1m: Optional[float] = None
    volatility_3m: Optional[float] = None
    volatility_1y: Optional[float] = None

    # 거래량
    avg_volume_3m: Optional[float] = None
    volume_change: Optional[float] = None

    # 뉴스/감성
    news_sentiment: Optional[float] = None  # -1 to 1
    news_volume: Optional[int] = None


class AlphaFactors(BaseModel):
    """32개 알파 팩터 점수"""
    symbol: str

    # 모멘텀 팩터 (7개)
    momentum_1m: Optional[float] = 0.0
    momentum_3m: Optional[float] = 0.0
    momentum_6m: Optional[float] = 0.0
    momentum_12m: Optional[float] = 0.0
    momentum_weighted: Optional[float] = 0.0  # 가중 평균 모멘텀
    reversal_1w: Optional[float] = 0.0  # 단기 반전
    trend_strength: Optional[float] = 0.0  # 추세 강도

    # 가치 팩터 (6개)
    value_pe: Optional[float] = 0.0
    value_pb: Optional[float] = 0.0
    value_ps: Optional[float] = 0.0
    value_pcf: Optional[float] = 0.0
    value_dividend: Optional[float] = 0.0
    value_composite: Optional[float] = 0.0  # 복합 가치 점수

    # 퀄리티 팩터 (6개)
    quality_roe: Optional[float] = 0.0
    quality_roa: Optional[float] = 0.0
    quality_debt: Optional[float] = 0.0  # 낮은 부채비율
    quality_liquidity: Optional[float] = 0.0  # 유동성 (Current Ratio)
    quality_growth: Optional[float] = 0.0  # 성장성
    quality_composite: Optional[float] = 0.0

    # 저변동성 팩터 (4개)
    low_vol_1m: Optional[float] = 0.0
    low_vol_3m: Optional[float] = 0.0
    low_vol_1y: Optional[float] = 0.0
    low_vol_composite: Optional[float] = 0.0

    # 사이즈 팩터 (3개)
    size_market_cap: Optional[float] = 0.0
    size_volume: Optional[float] = 0.0
    size_composite: Optional[float] = 0.0

    # 리스크 스프레드 팩터 (3개)
    risk_spread_credit: Optional[float] = 0.0
    risk_spread_volatility: Optional[float] = 0.0
    risk_spread_beta: Optional[float] = 0.0

    # 뉴스/감성 팩터 (2개)
    sentiment_score: Optional[float] = 0.0
    sentiment_momentum: Optional[float] = 0.0  # 감성 변화율

    # 변동성 스프레드 팩터 (1개)
    volatility_spread: Optional[float] = 0.0

    # 종합 점수
    total_score: float = 0.0
    rank: Optional[int] = None


class AlphaFactorCalculator:
    """알파 팩터 계산기"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_all_factors(self, stock_data: StockData) -> AlphaFactors:
        """
        32개 알파 팩터 계산

        Args:
            stock_data: 종목 데이터

        Returns:
            알파 팩터 점수
        """
        try:
            self.logger.debug(f"📊 {stock_data.symbol} 알파 팩터 계산 시작...")

            factors = AlphaFactors(symbol=stock_data.symbol)

            # 1. 모멘텀 팩터 계산
            self._calculate_momentum_factors(stock_data, factors)

            # 2. 가치 팩터 계산
            self._calculate_value_factors(stock_data, factors)

            # 3. 퀄리티 팩터 계산
            self._calculate_quality_factors(stock_data, factors)

            # 4. 저변동성 팩터 계산
            self._calculate_low_vol_factors(stock_data, factors)

            # 5. 사이즈 팩터 계산
            self._calculate_size_factors(stock_data, factors)

            # 6. 리스크 스프레드 팩터 계산
            self._calculate_risk_spread_factors(stock_data, factors)

            # 7. 뉴스/감성 팩터 계산
            self._calculate_sentiment_factors(stock_data, factors)

            # 8. 변동성 스프레드 팩터 계산
            self._calculate_volatility_spread_factors(stock_data, factors)

            # 9. 종합 점수 계산
            factors.total_score = self._calculate_total_score(factors)

            self.logger.debug(f"✅ {stock_data.symbol} 알파 팩터 계산 완료 (총점: {factors.total_score:.2f})")
            return factors

        except Exception as e:
            self.logger.error(f"❌ {stock_data.symbol} 알파 팩터 계산 실패: {e}")
            return AlphaFactors(symbol=stock_data.symbol, total_score=0.0)

    def _calculate_momentum_factors(self, data: StockData, factors: AlphaFactors):
        """모멘텀 팩터 계산 (7개)"""

        # 1개월 모멘텀
        if data.price_1m_ago and data.current_price:
            factors.momentum_1m = (data.current_price - data.price_1m_ago) / data.price_1m_ago

        # 3개월 모멘텀
        if data.price_3m_ago and data.current_price:
            factors.momentum_3m = (data.current_price - data.price_3m_ago) / data.price_3m_ago

        # 6개월 모멘텀
        if data.price_6m_ago and data.current_price:
            factors.momentum_6m = (data.current_price - data.price_6m_ago) / data.price_6m_ago

        # 12개월 모멘텀
        if data.price_1y_ago and data.current_price:
            factors.momentum_12m = (data.current_price - data.price_1y_ago) / data.price_1y_ago

        # 가중 평균 모멘텀 (최근 가중치 높음)
        momentums = []
        weights = []
        if factors.momentum_1m != 0:
            momentums.append(factors.momentum_1m)
            weights.append(0.4)
        if factors.momentum_3m != 0:
            momentums.append(factors.momentum_3m)
            weights.append(0.3)
        if factors.momentum_6m != 0:
            momentums.append(factors.momentum_6m)
            weights.append(0.2)
        if factors.momentum_12m != 0:
            momentums.append(factors.momentum_12m)
            weights.append(0.1)

        if momentums:
            factors.momentum_weighted = np.average(momentums, weights=weights)

        # 단기 반전 (1주일 모멘텀의 역) - 구현 생략 (데이터 필요)
        factors.reversal_1w = 0.0

        # 추세 강도 (모멘텀의 표준편차로 근사)
        if len(momentums) >= 2:
            factors.trend_strength = np.std(momentums)

    def _calculate_value_factors(self, data: StockData, factors: AlphaFactors):
        """가치 팩터 계산 (6개) - 낮을수록 좋음"""

        # P/E 비율 (역수로 변환하여 낮을수록 높은 점수)
        if data.pe_ratio and data.pe_ratio > 0:
            factors.value_pe = 1.0 / data.pe_ratio

        # P/B 비율
        if data.pb_ratio and data.pb_ratio > 0:
            factors.value_pb = 1.0 / data.pb_ratio

        # P/S 비율
        if data.ps_ratio and data.ps_ratio > 0:
            factors.value_ps = 1.0 / data.ps_ratio

        # P/CF 비율
        if data.pcf_ratio and data.pcf_ratio > 0:
            factors.value_pcf = 1.0 / data.pcf_ratio

        # 배당 수익률 (높을수록 좋음)
        if data.dividend_yield:
            factors.value_dividend = data.dividend_yield

        # 복합 가치 점수
        value_scores = [
            factors.value_pe,
            factors.value_pb,
            factors.value_ps,
            factors.value_pcf,
            factors.value_dividend
        ]
        value_scores = [v for v in value_scores if v != 0]
        if value_scores:
            factors.value_composite = np.mean(value_scores)

    def _calculate_quality_factors(self, data: StockData, factors: AlphaFactors):
        """퀄리티 팩터 계산 (6개)"""

        # ROE (높을수록 좋음)
        if data.roe:
            factors.quality_roe = data.roe / 100  # 정규화

        # ROA (높을수록 좋음)
        if data.roa:
            factors.quality_roa = data.roa / 100

        # 부채비율 (낮을수록 좋음)
        if data.debt_to_equity is not None:
            # 역수로 변환
            if data.debt_to_equity > 0:
                factors.quality_debt = 1.0 / (1.0 + data.debt_to_equity)
            else:
                factors.quality_debt = 1.0

        # 유동성 (Current Ratio, 높을수록 좋음)
        if data.current_ratio:
            factors.quality_liquidity = min(data.current_ratio / 2.0, 1.0)  # 2.0을 최대로 정규화

        # 성장성 (매출 + 이익 성장률)
        growth_scores = []
        if data.earnings_growth:
            growth_scores.append(data.earnings_growth / 100)
        if data.revenue_growth:
            growth_scores.append(data.revenue_growth / 100)
        if growth_scores:
            factors.quality_growth = np.mean(growth_scores)

        # 복합 퀄리티 점수
        quality_scores = [
            factors.quality_roe,
            factors.quality_roa,
            factors.quality_debt,
            factors.quality_liquidity,
            factors.quality_growth
        ]
        quality_scores = [q for q in quality_scores if q != 0]
        if quality_scores:
            factors.quality_composite = np.mean(quality_scores)

    def _calculate_low_vol_factors(self, data: StockData, factors: AlphaFactors):
        """저변동성 팩터 계산 (4개) - 낮을수록 좋음"""

        # 1개월 변동성 (역수)
        if data.volatility_1m and data.volatility_1m > 0:
            factors.low_vol_1m = 1.0 / (1.0 + data.volatility_1m)

        # 3개월 변동성 (역수)
        if data.volatility_3m and data.volatility_3m > 0:
            factors.low_vol_3m = 1.0 / (1.0 + data.volatility_3m)

        # 1년 변동성 (역수)
        if data.volatility_1y and data.volatility_1y > 0:
            factors.low_vol_1y = 1.0 / (1.0 + data.volatility_1y)

        # 복합 저변동성 점수
        vol_scores = [
            factors.low_vol_1m,
            factors.low_vol_3m,
            factors.low_vol_1y
        ]
        vol_scores = [v for v in vol_scores if v != 0]
        if vol_scores:
            factors.low_vol_composite = np.mean(vol_scores)

    def _calculate_size_factors(self, data: StockData, factors: AlphaFactors):
        """사이즈 팩터 계산 (3개)"""

        # 시가총액 (로그 스케일로 정규화)
        if data.market_cap and data.market_cap > 0:
            # 100억 이하: 0, 10조 이상: 1
            log_mcap = np.log10(data.market_cap)
            factors.size_market_cap = (log_mcap - 10) / 4  # 10 = 100억, 14 = 100조

        # 거래량 (로그 스케일)
        if data.avg_volume_3m and data.avg_volume_3m > 0:
            log_vol = np.log10(data.avg_volume_3m)
            factors.size_volume = (log_vol - 4) / 3  # 정규화

        # 복합 사이즈 점수
        size_scores = [factors.size_market_cap, factors.size_volume]
        size_scores = [s for s in size_scores if s != 0]
        if size_scores:
            factors.size_composite = np.mean(size_scores)

    def _calculate_risk_spread_factors(self, data: StockData, factors: AlphaFactors):
        """리스크 스프레드 팩터 계산 (3개)"""

        # 신용 스프레드 - 구현 생략 (채권 데이터 필요)
        factors.risk_spread_credit = 0.0

        # 변동성 스프레드 - 구현 생략
        factors.risk_spread_volatility = 0.0

        # 베타 스프레드 - 구현 생략 (시장 베타 필요)
        factors.risk_spread_beta = 0.0

    def _calculate_sentiment_factors(self, data: StockData, factors: AlphaFactors):
        """뉴스/감성 팩터 계산 (2개)"""

        # 감성 점수
        if data.news_sentiment is not None:
            factors.sentiment_score = data.news_sentiment

        # 감성 모멘텀 - 구현 생략 (과거 감성 데이터 필요)
        factors.sentiment_momentum = 0.0

    def _calculate_volatility_spread_factors(self, data: StockData, factors: AlphaFactors):
        """변동성 스프레드 팩터 계산 (1개)"""

        # 내재 변동성 vs 역사적 변동성 스프레드 - 구현 생략 (옵션 데이터 필요)
        factors.volatility_spread = 0.0

    def _calculate_total_score(self, factors: AlphaFactors) -> float:
        """
        총점 계산 - 팩터별 가중 평균

        가중치:
        - 모멘텀: 25%
        - 가치: 20%
        - 퀄리티: 20%
        - 저변동성: 15%
        - 사이즈: 10%
        - 리스크 스프레드: 5%
        - 감성: 3%
        - 변동성 스프레드: 2%
        """

        # 카테고리별 점수
        momentum_score = factors.momentum_weighted if factors.momentum_weighted else 0
        value_score = factors.value_composite if factors.value_composite else 0
        quality_score = factors.quality_composite if factors.quality_composite else 0
        low_vol_score = factors.low_vol_composite if factors.low_vol_composite else 0
        size_score = factors.size_composite if factors.size_composite else 0
        sentiment_score = factors.sentiment_score if factors.sentiment_score else 0

        # 가중 평균
        total = (
            momentum_score * 0.25 +
            value_score * 0.20 +
            quality_score * 0.20 +
            low_vol_score * 0.15 +
            size_score * 0.10 +
            sentiment_score * 0.03
        )

        return total


# 전역 인스턴스
_alpha_calculator = None


def get_alpha_calculator() -> AlphaFactorCalculator:
    """AlphaFactorCalculator 싱글톤 인스턴스 반환"""
    global _alpha_calculator
    if _alpha_calculator is None:
        _alpha_calculator = AlphaFactorCalculator()
    return _alpha_calculator


# 편의 함수
def calculate_alpha_factors(stock_data: StockData) -> AlphaFactors:
    """알파 팩터 계산 (편의 함수)"""
    calculator = get_alpha_calculator()
    return calculator.calculate_all_factors(stock_data)


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("알파 팩터 계산 시스템 테스트")
    print("=" * 80)

    # 테스트 데이터: 고성장 기술주
    test_stock_tech = StockData(
        symbol="NVDA",
        current_price=500.0,
        market_cap=1.2e12,  # 1.2조 달러
        price_1m_ago=480.0,
        price_3m_ago=450.0,
        price_6m_ago=400.0,
        price_1y_ago=350.0,
        pe_ratio=70.0,
        pb_ratio=40.0,
        ps_ratio=25.0,
        dividend_yield=0.02,
        roe=50.0,
        roa=25.0,
        debt_to_equity=0.3,
        current_ratio=2.5,
        earnings_growth=80.0,
        revenue_growth=60.0,
        volatility_1m=0.35,
        volatility_3m=0.40,
        volatility_1y=0.45,
        avg_volume_3m=50000000,
        news_sentiment=0.7
    )

    print("\n📊 종목 1: 고성장 기술주 (NVDA)")
    factors_tech = calculate_alpha_factors(test_stock_tech)
    print(f"   모멘텀 점수: {factors_tech.momentum_weighted:.4f}")
    print(f"   가치 점수: {factors_tech.value_composite:.4f}")
    print(f"   퀄리티 점수: {factors_tech.quality_composite:.4f}")
    print(f"   저변동성 점수: {factors_tech.low_vol_composite:.4f}")
    print(f"   사이즈 점수: {factors_tech.size_composite:.4f}")
    print(f"   감성 점수: {factors_tech.sentiment_score:.4f}")
    print(f"   🎯 총점: {factors_tech.total_score:.4f}")

    # 테스트 데이터: 가치주
    test_stock_value = StockData(
        symbol="JPM",
        current_price=150.0,
        market_cap=4.5e11,  # 450억 달러
        price_1m_ago=148.0,
        price_3m_ago=145.0,
        price_6m_ago=140.0,
        price_1y_ago=135.0,
        pe_ratio=10.0,
        pb_ratio=1.5,
        ps_ratio=3.0,
        dividend_yield=2.8,
        roe=15.0,
        roa=1.2,
        debt_to_equity=1.2,
        current_ratio=1.1,
        earnings_growth=8.0,
        revenue_growth=5.0,
        volatility_1m=0.18,
        volatility_3m=0.20,
        volatility_1y=0.22,
        avg_volume_3m=12000000,
        news_sentiment=0.1
    )

    print("\n📊 종목 2: 가치주 (JPM)")
    factors_value = calculate_alpha_factors(test_stock_value)
    print(f"   모멘텀 점수: {factors_value.momentum_weighted:.4f}")
    print(f"   가치 점수: {factors_value.value_composite:.4f}")
    print(f"   퀄리티 점수: {factors_value.quality_composite:.4f}")
    print(f"   저변동성 점수: {factors_value.low_vol_composite:.4f}")
    print(f"   사이즈 점수: {factors_value.size_composite:.4f}")
    print(f"   감성 점수: {factors_value.sentiment_score:.4f}")
    print(f"   🎯 총점: {factors_value.total_score:.4f}")
