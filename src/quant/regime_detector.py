"""
레짐 스위칭 시스템 (Regime-Switching System)

시장 상태를 4단계로 분류:
1. 저금리 확장기 (Low Rate Expansion) - 성장주 유리
2. 저금리 침체기 (Low Rate Recession) - 방어주, 채권 유리
3. 고금리 확장기 (High Rate Expansion) - 가치주 유리
4. 고금리 침체기 (High Rate Recession) - 현금, 금 유리
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """시장 레짐 (4단계)"""
    LOW_RATE_EXPANSION = "저금리_확장기"      # 성장주, 기술주 유리
    LOW_RATE_RECESSION = "저금리_침체기"      # 방어주, 채권 유리
    HIGH_RATE_EXPANSION = "고금리_확장기"     # 가치주, 금융주 유리
    HIGH_RATE_RECESSION = "고금리_침체기"     # 현금, 금, 채권 유리


class RegimeSignals(BaseModel):
    """레짐 판단 시그널"""
    interest_rate: float = Field(..., description="금리 수준 (%)")
    gdp_growth: float = Field(..., description="GDP 성장률 (%)")
    unemployment_rate: float = Field(..., description="실업률 (%)")
    inflation_rate: float = Field(..., description="인플레이션율 (%)")
    pmi: Optional[float] = Field(None, description="PMI 지수 (제조업)")
    credit_spread: Optional[float] = Field(None, description="신용 스프레드 (bp)")


class RegimeAnalysis(BaseModel):
    """레짐 분석 결과"""
    regime: MarketRegime = Field(..., description="현재 시장 레짐")
    confidence: float = Field(..., description="확신도 (0-1)")
    rate_environment: str = Field(..., description="금리 환경 (저금리/고금리)")
    economic_cycle: str = Field(..., description="경기 사이클 (확장/침체)")
    signals: RegimeSignals = Field(..., description="입력 시그널")
    reasoning: str = Field(..., description="판단 근거")
    recommended_sectors: list = Field(default_factory=list, description="추천 섹터")
    recommended_factors: list = Field(default_factory=list, description="추천 팩터")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class RegimeDetector:
    """레짐 감지기 - IQC 우승 전략의 핵심 컴포넌트"""

    # 임계값 설정
    RATE_THRESHOLD = 3.0  # 3% 이상이면 고금리로 판단
    GDP_THRESHOLD = 2.0   # 2% 이상이면 확장기로 판단
    UNEMPLOYMENT_CHANGE_THRESHOLD = 0.3  # 실업률 변화 임계값
    PMI_THRESHOLD = 50.0  # 50 이상이면 확장, 미만이면 침체

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_regime(self, signals: RegimeSignals) -> RegimeAnalysis:
        """
        레짐 감지 - 금리 환경 + 경기 사이클 조합

        Args:
            signals: 경제 시그널 데이터

        Returns:
            레짐 분석 결과
        """
        try:
            self.logger.info("🔍 시장 레짐 감지 시작...")

            # 1. 금리 환경 판단
            rate_environment = self._classify_rate_environment(signals.interest_rate)

            # 2. 경기 사이클 판단
            economic_cycle = self._classify_economic_cycle(signals)

            # 3. 레짐 결정
            regime = self._determine_regime(rate_environment, economic_cycle)

            # 4. 확신도 계산
            confidence = self._calculate_confidence(signals, regime)

            # 5. 추천 섹터 및 팩터 결정
            recommended_sectors = self._get_recommended_sectors(regime)
            recommended_factors = self._get_recommended_factors(regime)

            # 6. 판단 근거 생성
            reasoning = self._generate_reasoning(
                rate_environment,
                economic_cycle,
                signals
            )

            result = RegimeAnalysis(
                regime=regime,
                confidence=confidence,
                rate_environment=rate_environment,
                economic_cycle=economic_cycle,
                signals=signals,
                reasoning=reasoning,
                recommended_sectors=recommended_sectors,
                recommended_factors=recommended_factors
            )

            self.logger.info(f"✅ 레짐 감지 완료: {regime.value} (확신도: {confidence:.2%})")
            return result

        except Exception as e:
            self.logger.error(f"❌ 레짐 감지 실패: {e}")
            # 기본값 반환
            return RegimeAnalysis(
                regime=MarketRegime.LOW_RATE_EXPANSION,
                confidence=0.5,
                rate_environment="저금리",
                economic_cycle="확장기",
                signals=signals,
                reasoning="데이터 부족으로 기본 레짐 반환",
                recommended_sectors=["기술주"],
                recommended_factors=["모멘텀"]
            )

    def _classify_rate_environment(self, interest_rate: float) -> str:
        """금리 환경 분류"""
        if interest_rate >= self.RATE_THRESHOLD:
            return "고금리"
        else:
            return "저금리"

    def _classify_economic_cycle(self, signals: RegimeSignals) -> str:
        """경기 사이클 분류 (확장 vs 침체)"""

        # 여러 지표를 종합하여 판단
        expansion_score = 0
        recession_score = 0

        # 1. GDP 성장률
        if signals.gdp_growth >= self.GDP_THRESHOLD:
            expansion_score += 2
        else:
            recession_score += 2

        # 2. 실업률 (낮으면 확장)
        if signals.unemployment_rate < 4.5:
            expansion_score += 1
        elif signals.unemployment_rate > 6.0:
            recession_score += 2

        # 3. PMI (있으면 사용)
        if signals.pmi is not None:
            if signals.pmi >= self.PMI_THRESHOLD:
                expansion_score += 1
            else:
                recession_score += 1

        # 4. 인플레이션 (너무 낮으면 침체 신호)
        if signals.inflation_rate < 1.0:
            recession_score += 1
        elif 2.0 <= signals.inflation_rate <= 4.0:
            expansion_score += 1

        # 최종 판단
        if expansion_score > recession_score:
            return "확장기"
        else:
            return "침체기"

    def _determine_regime(self, rate_environment: str, economic_cycle: str) -> MarketRegime:
        """레짐 결정 (4가지 조합)"""

        if rate_environment == "저금리" and economic_cycle == "확장기":
            return MarketRegime.LOW_RATE_EXPANSION
        elif rate_environment == "저금리" and economic_cycle == "침체기":
            return MarketRegime.LOW_RATE_RECESSION
        elif rate_environment == "고금리" and economic_cycle == "확장기":
            return MarketRegime.HIGH_RATE_EXPANSION
        else:  # 고금리 + 침체기
            return MarketRegime.HIGH_RATE_RECESSION

    def _calculate_confidence(self, signals: RegimeSignals, regime: MarketRegime) -> float:
        """확신도 계산 (0-1)"""

        confidence = 0.5  # 기본 확신도

        # 데이터 품질에 따라 확신도 조정
        if signals.pmi is not None:
            confidence += 0.1

        if signals.credit_spread is not None:
            confidence += 0.1

        # 명확한 시그널일수록 확신도 증가
        if regime == MarketRegime.LOW_RATE_EXPANSION:
            if signals.gdp_growth > 3.0 and signals.interest_rate < 2.0:
                confidence += 0.2
        elif regime == MarketRegime.HIGH_RATE_RECESSION:
            if signals.gdp_growth < 1.0 and signals.interest_rate > 4.0:
                confidence += 0.2

        return min(confidence, 1.0)

    def _get_recommended_sectors(self, regime: MarketRegime) -> list:
        """레짐별 추천 섹터"""

        sector_map = {
            MarketRegime.LOW_RATE_EXPANSION: [
                "기술주", "소비재", "통신", "헬스케어"
            ],
            MarketRegime.LOW_RATE_RECESSION: [
                "방어주", "필수소비재", "유틸리티", "헬스케어"
            ],
            MarketRegime.HIGH_RATE_EXPANSION: [
                "가치주", "금융", "에너지", "산업재"
            ],
            MarketRegime.HIGH_RATE_RECESSION: [
                "현금성자산", "금", "채권", "필수소비재"
            ]
        }

        return sector_map.get(regime, ["다각화 포트폴리오"])

    def _get_recommended_factors(self, regime: MarketRegime) -> list:
        """레짐별 추천 알파 팩터"""

        factor_map = {
            MarketRegime.LOW_RATE_EXPANSION: [
                "모멘텀", "성장", "퀄리티", "저변동성"
            ],
            MarketRegime.LOW_RATE_RECESSION: [
                "가치", "배당", "저변동성", "퀄리티"
            ],
            MarketRegime.HIGH_RATE_EXPANSION: [
                "가치", "배당", "퀄리티", "사이즈"
            ],
            MarketRegime.HIGH_RATE_RECESSION: [
                "저변동성", "퀄리티", "가치", "배당"
            ]
        }

        return factor_map.get(regime, ["모멘텀", "가치"])

    def _generate_reasoning(
        self,
        rate_environment: str,
        economic_cycle: str,
        signals: RegimeSignals
    ) -> str:
        """판단 근거 생성"""

        reasoning = f"""
**시장 레짐 판단 근거**

📊 **금리 환경**: {rate_environment}
- 현재 금리: {signals.interest_rate:.2f}%
- 임계값: {self.RATE_THRESHOLD}%

📈 **경기 사이클**: {economic_cycle}
- GDP 성장률: {signals.gdp_growth:.2f}%
- 실업률: {signals.unemployment_rate:.2f}%
- 인플레이션: {signals.inflation_rate:.2f}%
"""

        if signals.pmi is not None:
            reasoning += f"- PMI: {signals.pmi:.1f}\n"

        reasoning += f"\n**종합 판단**: {rate_environment} + {economic_cycle}"

        return reasoning.strip()


# 전역 인스턴스
_regime_detector = None


def get_regime_detector() -> RegimeDetector:
    """RegimeDetector 싱글톤 인스턴스 반환"""
    global _regime_detector
    if _regime_detector is None:
        _regime_detector = RegimeDetector()
    return _regime_detector


# 편의 함수
def detect_current_regime(
    interest_rate: float,
    gdp_growth: float,
    unemployment_rate: float,
    inflation_rate: float,
    pmi: Optional[float] = None,
    credit_spread: Optional[float] = None
) -> RegimeAnalysis:
    """
    현재 시장 레짐 감지

    Args:
        interest_rate: 금리 (%)
        gdp_growth: GDP 성장률 (%)
        unemployment_rate: 실업률 (%)
        inflation_rate: 인플레이션율 (%)
        pmi: PMI 지수 (선택)
        credit_spread: 신용 스프레드 (선택)

    Returns:
        레짐 분석 결과
    """
    signals = RegimeSignals(
        interest_rate=interest_rate,
        gdp_growth=gdp_growth,
        unemployment_rate=unemployment_rate,
        inflation_rate=inflation_rate,
        pmi=pmi,
        credit_spread=credit_spread
    )

    detector = get_regime_detector()
    return detector.detect_regime(signals)


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("레짐 스위칭 시스템 테스트")
    print("=" * 80)

    # 시나리오 1: 저금리 확장기 (2020-2021 팬데믹 회복기)
    print("\n📊 시나리오 1: 저금리 확장기")
    result1 = detect_current_regime(
        interest_rate=0.5,
        gdp_growth=5.7,
        unemployment_rate=3.9,
        inflation_rate=2.3,
        pmi=55.0
    )
    print(f"   레짐: {result1.regime.value}")
    print(f"   확신도: {result1.confidence:.2%}")
    print(f"   추천 섹터: {', '.join(result1.recommended_sectors)}")
    print(f"   추천 팩터: {', '.join(result1.recommended_factors)}")

    # 시나리오 2: 고금리 침체기 (2023 금리 인상기)
    print("\n📊 시나리오 2: 고금리 침체기")
    result2 = detect_current_regime(
        interest_rate=5.5,
        gdp_growth=0.8,
        unemployment_rate=4.1,
        inflation_rate=3.7,
        pmi=48.0
    )
    print(f"   레짐: {result2.regime.value}")
    print(f"   확신도: {result2.confidence:.2%}")
    print(f"   추천 섹터: {', '.join(result2.recommended_sectors)}")
    print(f"   추천 팩터: {', '.join(result2.recommended_factors)}")

    # 시나리오 3: 고금리 확장기
    print("\n📊 시나리오 3: 고금리 확장기")
    result3 = detect_current_regime(
        interest_rate=4.5,
        gdp_growth=3.2,
        unemployment_rate=3.8,
        inflation_rate=2.8,
        pmi=52.0
    )
    print(f"   레짐: {result3.regime.value}")
    print(f"   확신도: {result3.confidence:.2%}")
    print(f"   추천 섹터: {', '.join(result3.recommended_sectors)}")
    print(f"   추천 팩터: {', '.join(result3.recommended_factors)}")
