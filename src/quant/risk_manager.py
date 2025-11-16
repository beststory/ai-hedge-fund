"""
리스크 관리 시스템 (Risk Management System)

IQC 전략의 리스크 관리 컴포넌트:
- 포트폴리오 리스크 지표 계산 (VaR, CVaR, MDD)
- 포지션 레벨 제약 조건 검증
- 동적 리스크 한도 관리
- 리스크 조정 및 경고
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import numpy as np

from src.quant.portfolio_optimizer import PortfolioRecommendation, PortfolioPosition

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """리스크 수준"""
    LOW = "낮음"
    MODERATE = "보통"
    HIGH = "높음"
    CRITICAL = "매우 높음"


class RiskMetrics(BaseModel):
    """포트폴리오 리스크 지표"""
    # VaR (Value at Risk)
    var_95: float = Field(..., description="95% 신뢰수준 VaR (%)")
    var_99: float = Field(..., description="99% 신뢰수준 VaR (%)")

    # CVaR (Conditional VaR / Expected Shortfall)
    cvar_95: float = Field(..., description="95% CVaR (%)")
    cvar_99: float = Field(..., description="99% CVaR (%)")

    # 최대 낙폭 (Maximum Drawdown)
    max_drawdown: float = Field(..., description="최대 예상 낙폭 (%)")

    # 변동성
    portfolio_volatility: float = Field(..., description="포트폴리오 변동성 (%)")
    annualized_volatility: float = Field(..., description="연환산 변동성 (%)")

    # 베타
    portfolio_beta: float = Field(default=0.0, description="시장 베타 (목표: 0)")

    # 집중도
    concentration_score: float = Field(..., description="집중도 점수 (0-1, 낮을수록 분산)")

    # 리스크 수준
    risk_level: RiskLevel = Field(..., description="종합 리스크 수준")

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class RiskConstraints(BaseModel):
    """리스크 제약 조건"""
    # 포지션 한도
    max_position_size: float = Field(default=0.10, description="최대 개별 포지션 크기 (10%)")
    max_sector_exposure: float = Field(default=0.30, description="최대 섹터 노출 (30%)")

    # 레버리지 한도
    max_gross_exposure: float = Field(default=2.0, description="최대 총 노출 (200%)")
    max_net_exposure: float = Field(default=0.20, description="최대 순 노출 (±20%)")

    # 변동성 한도
    max_portfolio_volatility: float = Field(default=15.0, description="최대 포트폴리오 변동성 (%)")
    max_drawdown_limit: float = Field(default=20.0, description="최대 낙폭 한도 (%)")

    # VaR 한도
    max_var_95: float = Field(default=10.0, description="최대 95% VaR (%)")
    max_var_99: float = Field(default=15.0, description="최대 99% VaR (%)")

    # 베타 한도
    max_beta: float = Field(default=0.30, description="최대 베타 (±0.3)")

    # 집중도 한도
    max_concentration: float = Field(default=0.50, description="최대 집중도 (0.5)")


class RiskViolation(BaseModel):
    """리스크 제약 위반"""
    constraint_name: str = Field(..., description="위반된 제약 조건")
    current_value: float = Field(..., description="현재 값")
    limit_value: float = Field(..., description="한도 값")
    severity: RiskLevel = Field(..., description="위반 심각도")
    recommendation: str = Field(..., description="권장 조치")


class RiskAssessment(BaseModel):
    """리스크 평가 결과"""
    metrics: RiskMetrics = Field(..., description="리스크 지표")
    constraints: RiskConstraints = Field(..., description="적용된 제약 조건")
    violations: List[RiskViolation] = Field(default_factory=list, description="위반 목록")
    is_acceptable: bool = Field(..., description="리스크 허용 가능 여부")
    overall_risk_level: RiskLevel = Field(..., description="종합 리스크 수준")
    recommendations: List[str] = Field(default_factory=list, description="리스크 관리 권장사항")


class RiskManager:
    """리스크 관리자"""

    def __init__(self, constraints: Optional[RiskConstraints] = None):
        """
        Args:
            constraints: 리스크 제약 조건 (기본값 사용 가능)
        """
        self.constraints = constraints or RiskConstraints()
        self.logger = logging.getLogger(__name__)

    def assess_risk(
        self,
        portfolio: PortfolioRecommendation,
        market_volatility: float = 20.0,  # 시장 변동성 (%)
        confidence_level: float = 0.95
    ) -> RiskAssessment:
        """
        포트폴리오 리스크 평가

        Args:
            portfolio: 포트폴리오 추천
            market_volatility: 현재 시장 변동성 (%)
            confidence_level: 신뢰수준 (0.95 or 0.99)

        Returns:
            리스크 평가 결과
        """
        try:
            self.logger.info("🔍 포트폴리오 리스크 평가 시작...")

            # 1. 리스크 지표 계산
            metrics = self._calculate_risk_metrics(portfolio, market_volatility)

            # 2. 제약 조건 검증
            violations = self._check_constraints(portfolio, metrics)

            # 3. 종합 리스크 수준 판단
            overall_risk = self._determine_overall_risk(metrics, violations)

            # 4. 권장사항 생성
            recommendations = self._generate_recommendations(violations, metrics)

            # 5. 허용 가능 여부 판단
            is_acceptable = len([v for v in violations if v.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]]) == 0

            assessment = RiskAssessment(
                metrics=metrics,
                constraints=self.constraints,
                violations=violations,
                is_acceptable=is_acceptable,
                overall_risk_level=overall_risk,
                recommendations=recommendations
            )

            self.logger.info(f"✅ 리스크 평가 완료: {overall_risk.value}")
            self.logger.info(f"   위반 건수: {len(violations)}개")
            self.logger.info(f"   허용 가능: {'예' if is_acceptable else '아니오'}")

            return assessment

        except Exception as e:
            self.logger.error(f"❌ 리스크 평가 실패: {e}")
            raise

    def _calculate_risk_metrics(
        self,
        portfolio: PortfolioRecommendation,
        market_volatility: float
    ) -> RiskMetrics:
        """리스크 지표 계산"""

        # 포트폴리오 변동성 (예상값 사용)
        portfolio_vol = portfolio.expected_volatility
        annualized_vol = portfolio_vol * np.sqrt(252)  # 연환산

        # VaR 계산 (정규분포 가정)
        var_95 = 1.645 * portfolio_vol  # 95% 신뢰수준
        var_99 = 2.326 * portfolio_vol  # 99% 신뢰수준

        # CVaR 계산 (정규분포 가정)
        cvar_95 = portfolio_vol * 2.063  # CVaR는 VaR보다 큼
        cvar_99 = portfolio_vol * 2.665

        # 최대 낙폭 추정 (변동성 기반)
        max_drawdown = portfolio_vol * 3.0  # 3-sigma 이벤트

        # 베타 계산 (순 노출 기반 근사)
        portfolio_beta = abs(portfolio.net_exposure) / portfolio.gross_exposure if portfolio.gross_exposure > 0 else 0.0

        # 집중도 계산 (Herfindahl Index)
        concentration = self._calculate_concentration(portfolio)

        # 종합 리스크 수준 판단
        risk_level = self._classify_risk_level(portfolio_vol, var_95, max_drawdown)

        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown=max_drawdown,
            portfolio_volatility=portfolio_vol,
            annualized_volatility=annualized_vol,
            portfolio_beta=portfolio_beta,
            concentration_score=concentration,
            risk_level=risk_level
        )

    def _calculate_concentration(self, portfolio: PortfolioRecommendation) -> float:
        """
        집중도 계산 (Herfindahl-Hirschman Index)

        Returns:
            집중도 점수 (0-1, 1에 가까울수록 집중)
        """
        all_positions = portfolio.long_positions + portfolio.short_positions
        total_allocation = sum(abs(p.allocation) for p in all_positions)

        if total_allocation == 0:
            return 0.0

        # HHI 계산
        hhi = sum((abs(p.allocation) / total_allocation) ** 2 for p in all_positions)

        return hhi

    def _classify_risk_level(
        self,
        volatility: float,
        var_95: float,
        max_drawdown: float
    ) -> RiskLevel:
        """리스크 수준 분류"""

        # 여러 지표를 종합하여 판단
        if volatility > 20.0 or var_95 > 12.0 or max_drawdown > 25.0:
            return RiskLevel.CRITICAL
        elif volatility > 15.0 or var_95 > 10.0 or max_drawdown > 20.0:
            return RiskLevel.HIGH
        elif volatility > 10.0 or var_95 > 7.0 or max_drawdown > 15.0:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    def _check_constraints(
        self,
        portfolio: PortfolioRecommendation,
        metrics: RiskMetrics
    ) -> List[RiskViolation]:
        """제약 조건 검증"""

        violations = []

        # 1. 포지션 크기 검증
        for pos in portfolio.long_positions + portfolio.short_positions:
            if pos.weight > self.constraints.max_position_size * 100:
                violations.append(RiskViolation(
                    constraint_name="최대 포지션 크기",
                    current_value=pos.weight,
                    limit_value=self.constraints.max_position_size * 100,
                    severity=RiskLevel.HIGH,
                    recommendation=f"{pos.symbol} 포지션을 {self.constraints.max_position_size * 100}% 이하로 축소"
                ))

        # 2. 총 노출 검증
        gross_exposure_pct = portfolio.gross_exposure / (portfolio.total_long_exposure + portfolio.total_short_exposure) * 2.0 if (portfolio.total_long_exposure + portfolio.total_short_exposure) > 0 else 0
        if gross_exposure_pct > self.constraints.max_gross_exposure:
            violations.append(RiskViolation(
                constraint_name="최대 총 노출",
                current_value=gross_exposure_pct,
                limit_value=self.constraints.max_gross_exposure,
                severity=RiskLevel.HIGH,
                recommendation=f"총 노출을 {self.constraints.max_gross_exposure * 100}% 이하로 축소"
            ))

        # 3. 순 노출 검증
        total_capital = portfolio.total_long_exposure + portfolio.total_short_exposure
        net_exposure_pct = abs(portfolio.net_exposure) / total_capital if total_capital > 0 else 0
        if net_exposure_pct > self.constraints.max_net_exposure:
            violations.append(RiskViolation(
                constraint_name="최대 순 노출",
                current_value=net_exposure_pct * 100,
                limit_value=self.constraints.max_net_exposure * 100,
                severity=RiskLevel.MODERATE,
                recommendation="시장 중립성 개선을 위해 롱/숏 밸런스 조정"
            ))

        # 4. 변동성 검증
        if metrics.portfolio_volatility > self.constraints.max_portfolio_volatility:
            violations.append(RiskViolation(
                constraint_name="최대 포트폴리오 변동성",
                current_value=metrics.portfolio_volatility,
                limit_value=self.constraints.max_portfolio_volatility,
                severity=RiskLevel.HIGH,
                recommendation="저변동성 주식 비중 증대 또는 레버리지 축소"
            ))

        # 5. VaR 검증
        if metrics.var_95 > self.constraints.max_var_95:
            violations.append(RiskViolation(
                constraint_name="최대 95% VaR",
                current_value=metrics.var_95,
                limit_value=self.constraints.max_var_95,
                severity=RiskLevel.HIGH,
                recommendation="포지션 크기 축소 또는 헤지 추가"
            ))

        # 6. 베타 검증
        if abs(metrics.portfolio_beta) > self.constraints.max_beta:
            violations.append(RiskViolation(
                constraint_name="최대 베타",
                current_value=metrics.portfolio_beta,
                limit_value=self.constraints.max_beta,
                severity=RiskLevel.MODERATE,
                recommendation="시장 중립성 개선 (롱/숏 밸런싱)"
            ))

        # 7. 집중도 검증
        if metrics.concentration_score > self.constraints.max_concentration:
            violations.append(RiskViolation(
                constraint_name="최대 집중도",
                current_value=metrics.concentration_score,
                limit_value=self.constraints.max_concentration,
                severity=RiskLevel.MODERATE,
                recommendation="포지션 분산도 개선 (더 많은 종목으로 분산)"
            ))

        return violations

    def _determine_overall_risk(
        self,
        metrics: RiskMetrics,
        violations: List[RiskViolation]
    ) -> RiskLevel:
        """종합 리스크 수준 판단"""

        # 위반 중 가장 심각한 수준 선택
        if violations:
            max_severity = max(v.severity for v in violations)
            # 메트릭의 리스크 수준과 비교하여 더 높은 것 선택
            severity_order = [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]
            metric_idx = severity_order.index(metrics.risk_level)
            violation_idx = severity_order.index(max_severity)
            return severity_order[max(metric_idx, violation_idx)]
        else:
            return metrics.risk_level

    def _generate_recommendations(
        self,
        violations: List[RiskViolation],
        metrics: RiskMetrics
    ) -> List[str]:
        """리스크 관리 권장사항 생성"""

        recommendations = []

        # 위반 사항별 권장사항
        for v in violations:
            recommendations.append(f"⚠️ {v.constraint_name}: {v.recommendation}")

        # 일반적인 권장사항
        if metrics.risk_level == RiskLevel.HIGH or metrics.risk_level == RiskLevel.CRITICAL:
            recommendations.append("🚨 전체적인 리스크 수준이 높습니다. 포지션 크기를 줄이거나 헤지를 추가하세요.")

        if metrics.concentration_score > 0.3:
            recommendations.append("📊 포트폴리오 집중도가 높습니다. 더 많은 종목으로 분산하세요.")

        if abs(metrics.portfolio_beta) > 0.2:
            recommendations.append("📈 베타가 높아 시장 중립성이 낮습니다. 롱/숏 밸런스를 조정하세요.")

        if not recommendations:
            recommendations.append("✅ 리스크 관리 상태가 양호합니다.")

        return recommendations

    def adjust_portfolio_for_risk(
        self,
        portfolio: PortfolioRecommendation,
        assessment: RiskAssessment,
        adjustment_factor: float = 0.8
    ) -> PortfolioRecommendation:
        """
        리스크 조정된 포트폴리오 생성

        Args:
            portfolio: 원본 포트폴리오
            assessment: 리스크 평가 결과
            adjustment_factor: 조정 계수 (0.8 = 20% 축소)

        Returns:
            조정된 포트폴리오
        """
        if assessment.is_acceptable:
            self.logger.info("✅ 리스크가 허용 범위 내입니다. 조정 불필요.")
            return portfolio

        self.logger.info(f"🔧 리스크 조정 중... (조정 계수: {adjustment_factor})")

        # 포지션 크기 축소
        adjusted_long = []
        for pos in portfolio.long_positions:
            adjusted_pos = pos.model_copy()
            adjusted_pos.allocation *= adjustment_factor
            adjusted_pos.shares = int(adjusted_pos.shares * adjustment_factor)
            adjusted_pos.weight *= adjustment_factor
            adjusted_long.append(adjusted_pos)

        adjusted_short = []
        for pos in portfolio.short_positions:
            adjusted_pos = pos.model_copy()
            adjusted_pos.allocation *= adjustment_factor
            adjusted_pos.shares = int(adjusted_pos.shares * adjustment_factor)
            adjusted_pos.weight *= adjustment_factor
            adjusted_short.append(adjusted_pos)

        # 조정된 포트폴리오 생성
        adjusted_portfolio = portfolio.model_copy()
        adjusted_portfolio.long_positions = adjusted_long
        adjusted_portfolio.short_positions = adjusted_short
        adjusted_portfolio.total_long_exposure *= adjustment_factor
        adjusted_portfolio.total_short_exposure *= adjustment_factor
        adjusted_portfolio.net_exposure *= adjustment_factor
        adjusted_portfolio.gross_exposure *= adjustment_factor
        adjusted_portfolio.expected_volatility *= adjustment_factor

        self.logger.info(f"✅ 리스크 조정 완료")

        return adjusted_portfolio


# 전역 인스턴스
_risk_manager = None


def get_risk_manager(constraints: Optional[RiskConstraints] = None) -> RiskManager:
    """RiskManager 싱글톤 인스턴스 반환"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(constraints)
    return _risk_manager


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)

    from src.quant.regime_detector import detect_current_regime
    from src.quant.alpha_factors import AlphaFactorCalculator, StockData
    from src.quant.portfolio_optimizer import LongShortOptimizer

    print("=" * 80)
    print("리스크 관리 시스템 테스트")
    print("=" * 80)

    # 1. 포트폴리오 생성
    regime_analysis = detect_current_regime(
        interest_rate=5.5,
        gdp_growth=2.1,
        unemployment_rate=3.7,
        inflation_rate=3.1,
        pmi=51.0
    )

    calculator = AlphaFactorCalculator()
    stocks = []

    # 샘플 주식 데이터
    for i in range(10):
        stock = StockData(
            symbol=f"STOCK{i}",
            current_price=100.0 + i * 10,
            market_cap=100_000_000_000,
            price_1m_ago=95.0,
            price_3m_ago=90.0,
            price_6m_ago=85.0,
            price_1y_ago=80.0,
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
        factors = calculator.calculate_all_factors(stock)
        stocks.append((stock, factors))

    optimizer = LongShortOptimizer(num_long=5, num_short=5)
    portfolio = optimizer.optimize_portfolio(
        stocks=stocks,
        regime_analysis=regime_analysis,
        total_capital=1_000_000.0
    )

    # 2. 리스크 평가
    risk_manager = RiskManager()
    assessment = risk_manager.assess_risk(
        portfolio=portfolio,
        market_volatility=20.0
    )

    # 3. 결과 출력
    print("\n" + "=" * 80)
    print("📊 리스크 지표")
    print("=" * 80)
    print(f"포트폴리오 변동성:    {assessment.metrics.portfolio_volatility:.2f}%")
    print(f"연환산 변동성:        {assessment.metrics.annualized_volatility:.2f}%")
    print(f"95% VaR:            {assessment.metrics.var_95:.2f}%")
    print(f"99% VaR:            {assessment.metrics.var_99:.2f}%")
    print(f"95% CVaR:           {assessment.metrics.cvar_95:.2f}%")
    print(f"예상 최대 낙폭:       {assessment.metrics.max_drawdown:.2f}%")
    print(f"포트폴리오 베타:      {assessment.metrics.portfolio_beta:.3f}")
    print(f"집중도 점수:          {assessment.metrics.concentration_score:.3f}")
    print(f"리스크 수준:          {assessment.metrics.risk_level.value}")

    print("\n" + "=" * 80)
    print("⚖️ 제약 조건 검증")
    print("=" * 80)
    print(f"허용 가능 여부:       {'✅ 예' if assessment.is_acceptable else '❌ 아니오'}")
    print(f"종합 리스크 수준:     {assessment.overall_risk_level.value}")
    print(f"위반 건수:           {len(assessment.violations)}개")

    if assessment.violations:
        print("\n⚠️ 위반 목록:")
        for v in assessment.violations:
            print(f"  - {v.constraint_name}: {v.current_value:.2f} (한도: {v.limit_value:.2f})")
            print(f"    심각도: {v.severity.value}, 권장: {v.recommendation}")

    print("\n" + "=" * 80)
    print("💡 권장사항")
    print("=" * 80)
    for rec in assessment.recommendations:
        print(f"  {rec}")

    print("=" * 80)
