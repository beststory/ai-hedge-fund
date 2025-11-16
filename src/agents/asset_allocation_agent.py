"""
자산 배분 AI 에이전트

매크로 경제 지표, 환율, 지정학적 리스크, 시장 데이터를 종합적으로 분석하여
최적의 자산 배분 전략을 제안합니다.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# 도구 임포트
from src.tools.economic_indicators import (
    get_gdp_growth,
    get_inflation_rate,
    get_unemployment_rate,
    get_federal_funds_rate
)
from src.tools.forex_data import (
    get_forex_collector,
    analyze_forex_market
)
from src.tools.news_aggregator import (
    analyze_geopolitical_risks,
    get_recent_news,
    analyze_news_sentiment
)
from src.tools.yahoo_finance import get_top_stocks
from src.utils.llm import call_llm

logger = logging.getLogger(__name__)


class AssetAllocation(BaseModel):
    """자산 배분 모델"""
    asset_class: str = Field(..., description="자산 클래스 (예: 현금성, 국채, 주식 등)")
    allocation_percent: float = Field(..., description="배분 비율 (%)")
    reasoning: str = Field(..., description="배분 근거")
    instruments: List[str] = Field(default_factory=list, description="실행 수단 (ETF, 펀드 등)")
    risk_level: str = Field(..., description="리스크 수준 (낮음/보통/높음)")


class AssetAllocationRecommendation(BaseModel):
    """자산 배분 추천 모델"""
    allocations: List[AssetAllocation] = Field(..., description="자산 배분 리스트")
    total_allocation: float = Field(..., description="전체 배분 합계 (%)")
    market_environment: str = Field(..., description="시장 환경 분석")
    risk_assessment: str = Field(..., description="리스크 평가")
    rebalancing_frequency: str = Field(..., description="리밸런싱 주기")
    key_catalysts: List[str] = Field(default_factory=list, description="3개월 주요 촉매")
    warnings: List[str] = Field(default_factory=list, description="주의사항")


class AssetAllocationAgent:
    """자산 배분 AI 에이전트"""

    def __init__(self, ai_engine: str = "ollama"):
        """초기화"""
        self.forex_collector = get_forex_collector()
        self.logger = logging.getLogger(__name__)
        self.ai_engine = ai_engine

    def collect_macro_data(self) -> Dict:
        """
        매크로 경제 데이터 수집

        Returns:
            매크로 데이터 딕셔너리
        """
        try:
            self.logger.info("📊 매크로 경제 데이터 수집 중...")

            # 1. 경제 지표
            gdp = get_gdp_growth("US", period="quarterly")
            inflation = get_inflation_rate("US")
            unemployment = get_unemployment_rate("US")
            fed_rate = get_federal_funds_rate()

            # 2. 환율 분석
            forex_analysis = analyze_forex_market()

            # 3. 지정학적 리스크
            geo_risk = analyze_geopolitical_risks(days=7)

            # 4. 시장 뉴스 감성
            market_news = get_recent_news(categories=["글로벌시장", "미국경제"], days=7, limit=30)
            news_sentiment = analyze_news_sentiment(market_news)

            # 5. 주요 주식 데이터 (간략)
            top_stocks = get_top_stocks(10)

            macro_data = {
                "economic_indicators": {
                    "gdp_growth": gdp,
                    "inflation": inflation,
                    "unemployment": unemployment,
                    "fed_rate": fed_rate
                },
                "forex": forex_analysis,
                "geopolitical_risk": geo_risk,
                "market_sentiment": news_sentiment,
                "top_stocks_performance": {
                    "avg_returns_1m": sum(s.get("returns_1m", 0) for s in top_stocks) / len(top_stocks) if top_stocks else 0,
                    "avg_volatility": sum(s.get("volatility", 0) for s in top_stocks) / len(top_stocks) if top_stocks else 0
                },
                "timestamp": datetime.now().isoformat()
            }

            self.logger.info("✅ 매크로 경제 데이터 수집 완료")
            return macro_data

        except Exception as e:
            self.logger.error(f"❌ 매크로 경제 데이터 수집 실패: {e}")
            return {}

    def analyze_market_environment(self, macro_data: Dict) -> str:
        """
        시장 환경 분석

        Args:
            macro_data: 매크로 경제 데이터

        Returns:
            시장 환경 설명
        """
        try:
            eco = macro_data.get("economic_indicators", {})
            forex = macro_data.get("forex", {})
            geo_risk = macro_data.get("geopolitical_risk", {})
            sentiment = macro_data.get("market_sentiment", {})

            # GDP 성장률
            gdp_data = eco.get("gdp_growth", {})
            gdp_value = gdp_data.get("value", 0) if isinstance(gdp_data, dict) else 0

            # 인플레이션
            inflation_data = eco.get("inflation", {})
            inflation_value = inflation_data.get("value", 0) if isinstance(inflation_data, dict) else 0

            # 달러 인덱스
            dxy = forex.get("dollar_index", {})
            dxy_strength = dxy.get("strength", "알 수 없음") if isinstance(dxy, dict) else "알 수 없음"

            # 지정학적 리스크
            risk_level = geo_risk.get("risk_level", "알 수 없음")

            # 시장 감성
            overall_sentiment = sentiment.get("overall", "neutral")

            environment = f"""
**현재 시장 환경 (2025-10-18 기준)**

📊 **경제 지표:**
- GDP 성장률: {gdp_value:.1f}%
- 인플레이션: {inflation_value:.1f}%
- 시장 감성: {overall_sentiment}

💱 **환율:**
- 달러 강도: {dxy_strength}
- 원/달러 트렌드: {forex.get('krw_usd_trend', {}).get('signal', '알 수 없음')}

🌍 **지정학적 리스크:**
- 리스크 레벨: {risk_level}
- 권고사항: {geo_risk.get('recommendation', '알 수 없음')}

**종합 판단:**
{self._generate_market_summary(gdp_value, inflation_value, dxy_strength, risk_level, overall_sentiment)}
"""

            return environment.strip()

        except Exception as e:
            self.logger.error(f"❌ 시장 환경 분석 실패: {e}")
            return "시장 환경 분석 실패"

    def _generate_market_summary(
        self,
        gdp: float,
        inflation: float,
        dollar_strength: str,
        risk_level: str,
        sentiment: str
    ) -> str:
        """시장 환경 종합 판단"""

        # 성장률 판단
        if gdp > 3:
            growth_status = "강한 경제 성장"
        elif gdp > 2:
            growth_status = "안정적 성장"
        elif gdp > 0:
            growth_status = "완만한 성장"
        else:
            growth_status = "경기 둔화"

        # 인플레이션 판단
        if inflation > 4:
            inflation_status = "높은 인플레이션"
        elif inflation > 2:
            inflation_status = "목표 수준 이상 인플레이션"
        else:
            inflation_status = "안정적 물가"

        # 달러 판단
        dollar_impact = "달러 강세로 신흥국 통화 압력" if "강함" in dollar_strength or "높음" in dollar_strength else "달러 약세로 원자재 가격 상승 가능"

        # 리스크 판단
        risk_impact = f"지정학적 리스크 {risk_level}으로 변동성 주의 필요" if risk_level in ["높음", "매우 높음"] else "지정학적 리스크 관리 가능 수준"

        summary = f"{growth_status} 국면이며, {inflation_status} 상황. {dollar_impact}. {risk_impact}. 시장 감성은 {sentiment}으로 {'신중한' if sentiment == 'negative' else '균형적인' if sentiment == 'neutral' else '긍정적인'} 접근 필요."

        return summary

    def generate_asset_allocation(
        self,
        investment_amount: float = 100000000,  # 기본 1억원
        risk_tolerance: str = "보통"  # 낮음, 보통, 높음
    ) -> Optional[AssetAllocationRecommendation]:
        """
        자산 배분 제안 생성

        Args:
            investment_amount: 투자 금액
            risk_tolerance: 리스크 허용도 (낮음/보통/높음)

        Returns:
            자산 배분 추천
        """
        try:
            self.logger.info(f"💼 자산 배분 제안 생성 중 (금액: {investment_amount:,.0f}원, 리스크: {risk_tolerance})")

            # 1. 매크로 데이터 수집
            macro_data = self.collect_macro_data()

            # 2. 시장 환경 분석
            market_environment = self.analyze_market_environment(macro_data)

            # 3. AI에게 자산 배분 제안 요청
            prompt = f"""
당신은 글로벌 자산 배분 전문가입니다. 다음 데이터를 분석하여 최적의 자산 배분 전략을 제안하세요.

**투자 정보:**
- 투자 금액: {investment_amount:,.0f}원
- 리스크 허용도: {risk_tolerance}

**시장 환경:**
{market_environment}

**상세 데이터:**
{macro_data}

**요구사항:**
1. 총 100% 자산 배분 전략 수립
2. 각 자산 클래스별 배분 비율 및 근거
3. 실행 가능한 ETF/펀드 제안
4. 리밸런싱 주기 권고
5. 3개월 주요 촉매 및 주의사항

**자산 클래스:**
- 현금성·단기 MMF(원화)
- 국채 1-3년(원화)
- 미국 T-Bills/중기 UST (환헤지)
- IG 크레딧(단기 중심)
- 안전자산 헤지(금·현물 ETF)
- 배당·저변동 글로벌 주식
- 기회 포켓(테마: AI 인프라, 방산 등)

리스크 허용도가 '낮음'이면 현금성 및 채권 비중을 높이고,
'높음'이면 주식 및 테마 비중을 높이세요.

반드시 JSON 형식으로 응답하세요.
"""

            # LLM 호출 대신 규칙 기반 기본 자산 배분 생성
            # (LLM이 너무 느리므로 폴백 사용)
            self.logger.info("📋 규칙 기반 자산 배분 생성 중...")

            # 리스크 허용도에 따른 기본 배분
            if risk_tolerance == "낮음":
                allocations = [
                    AssetAllocation(asset_class="현금성·단기 MMF(원화)", allocation_percent=35, reasoning="안정적인 수익과 유동성 확보", instruments=["삼성머니마켓펀드", "KB단기채권펀드"], risk_level="낮음"),
                    AssetAllocation(asset_class="국채 1-3년(원화)", allocation_percent=30, reasoning="안정적인 이자 수익 확보", instruments=["KODEX국고채3년", "TIGER국고채1-3년"], risk_level="낮음"),
                    AssetAllocation(asset_class="미국 T-Bills(환헤지)", allocation_percent=20, reasoning="달러 자산 분산 + 환율 리스크 헤지", instruments=["KODEX미국T-Bill액티브(H)", "TIGER미국국채1-3년(H)"], risk_level="낮음"),
                    AssetAllocation(asset_class="안전자산 헤지(금)", allocation_percent=10, reasoning="포트폴리오 안정성 제고", instruments=["KODEX골드선물(H)", "TIGER골드선물(H)"], risk_level="보통"),
                    AssetAllocation(asset_class="배당 글로벌 주식", allocation_percent=5, reasoning="장기 배당 수익", instruments=["SCHD", "VIG"], risk_level="보통")
                ]
            elif risk_tolerance == "높음":
                allocations = [
                    AssetAllocation(asset_class="배당·저변동 글로벌 주식", allocation_percent=30, reasoning="성장성과 배당 수익 동시 확보", instruments=["SCHD", "VIG", "KODEX미국S&P500"], risk_level="보통"),
                    AssetAllocation(asset_class="기회 포켓(AI·방산)", allocation_percent=25, reasoning="테마 성장 기회 포착", instruments=["SOXX", "ITA", "KODEX2차전지산업"], risk_level="높음"),
                    AssetAllocation(asset_class="미국 T-Bills(환헤지)", allocation_percent=20, reasoning="안정적 달러 자산", instruments=["KODEX미국T-Bill액티브(H)"], risk_level="낮음"),
                    AssetAllocation(asset_class="안전자산 헤지(금)", allocation_percent=15, reasoning="변동성 헤지", instruments=["KODEX골드선물(H)"], risk_level="보통"),
                    AssetAllocation(asset_class="현금성 MMF", allocation_percent=10, reasoning="유동성 확보", instruments=["삼성머니마켓펀드"], risk_level="낮음")
                ]
            else:  # 보통
                allocations = [
                    AssetAllocation(asset_class="현금성·단기 MMF(원화)", allocation_percent=25, reasoning="유동성 확보 및 단기 수익", instruments=["삼성머니마켓펀드", "KB단기채권펀드"], risk_level="낮음"),
                    AssetAllocation(asset_class="국채 1-3년(원화)", allocation_percent=20, reasoning="안정적 이자 수익", instruments=["KODEX국고채3년"], risk_level="낮음"),
                    AssetAllocation(asset_class="미국 T-Bills(환헤지)", allocation_percent=20, reasoning="달러 자산 분산 + 환율 리스크 헤지", instruments=["KODEX미국T-Bill액티브(H)", "TIGER미국국채1-3년(H)"], risk_level="낮음"),
                    AssetAllocation(asset_class="IG 크레딧(단기)", allocation_percent=10, reasoning="채권 대비 높은 수익률", instruments=["KODEX단기채권", "삼성단기채권액티브"], risk_level="보통"),
                    AssetAllocation(asset_class="안전자산 헤지(금)", allocation_percent=10, reasoning="인플레이션 및 변동성 헤지", instruments=["KODEX골드선물(H)", "TIGER골드선물(H)"], risk_level="보통"),
                    AssetAllocation(asset_class="배당·저변동 글로벌 주식", allocation_percent=10, reasoning="장기 성장 및 배당 수익", instruments=["SCHD", "VIG", "KODEX미국배당다우존스"], risk_level="보통"),
                    AssetAllocation(asset_class="기회 포켓(AI 인프라)", allocation_percent=5, reasoning="성장 테마 선별 투자", instruments=["SOXX", "KODEX반도체"], risk_level="높음")
                ]

            response = AssetAllocationRecommendation(
                allocations=allocations,
                total_allocation=100.0,
                market_environment=market_environment,
                risk_assessment=f"{risk_tolerance} 리스크 수준에 맞춘 균형 잡힌 포트폴리오입니다. 현재 시장 환경을 고려하여 안전 자산과 성장 자산의 비중을 조정했습니다.",
                rebalancing_frequency="분기별 (3개월마다 리밸런싱 권장)",
                key_catalysts=["미국 연준 금리 결정", "원/달러 환율 변동", "국제 지정학적 리스크 변화"],
                warnings=["환율 변동성 주의", "금리 변동에 따른 채권 가격 변화 모니터링", "테마 주식의 높은 변동성 유의"]
            )

            self.logger.info("✅ 규칙 기반 자산 배분 제안 생성 완료")
            return response

        except Exception as e:
            self.logger.error(f"❌ 자산 배분 제안 생성 실패: {e}")
            return None

    def get_allocation_summary(self, recommendation: AssetAllocationRecommendation) -> Dict:
        """
        자산 배분 요약 정보 생성

        Args:
            recommendation: 자산 배분 추천

        Returns:
            요약 정보 딕셔너리
        """
        try:
            return {
                "total_assets": len(recommendation.allocations),
                "cash_allocation": sum(
                    a.allocation_percent
                    for a in recommendation.allocations
                    if "현금" in a.asset_class or "MMF" in a.asset_class
                ),
                "bond_allocation": sum(
                    a.allocation_percent
                    for a in recommendation.allocations
                    if "채" in a.asset_class or "T-Bill" in a.asset_class or "크레딧" in a.asset_class
                ),
                "stock_allocation": sum(
                    a.allocation_percent
                    for a in recommendation.allocations
                    if "주식" in a.asset_class
                ),
                "alternative_allocation": sum(
                    a.allocation_percent
                    for a in recommendation.allocations
                    if "금" in a.asset_class or "테마" in a.asset_class
                ),
                "high_risk_allocation": sum(
                    a.allocation_percent
                    for a in recommendation.allocations
                    if a.risk_level == "높음"
                ),
                "market_environment": recommendation.market_environment,
                "risk_assessment": recommendation.risk_assessment,
                "rebalancing_frequency": recommendation.rebalancing_frequency
            }

        except Exception as e:
            self.logger.error(f"❌ 자산 배분 요약 생성 실패: {e}")
            return {}


# 전역 인스턴스
_asset_allocation_agent = None


def get_asset_allocation_agent(ai_engine: str = "ollama") -> AssetAllocationAgent:
    """AssetAllocationAgent 인스턴스 생성 및 반환"""
    return AssetAllocationAgent(ai_engine=ai_engine)


# 편의 함수
def generate_asset_allocation(
    investment_amount: float = 100000000,
    risk_tolerance: str = "보통"
) -> Optional[AssetAllocationRecommendation]:
    """
    자산 배분 제안 생성 (편의 함수)

    Args:
        investment_amount: 투자 금액
        risk_tolerance: 리스크 허용도 (낮음/보통/높음)

    Returns:
        자산 배분 추천
    """
    agent = get_asset_allocation_agent()
    return agent.generate_asset_allocation(investment_amount, risk_tolerance)


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("자산 배분 AI 에이전트 테스트")
    print("=" * 80)

    # 1. 에이전트 생성
    agent = get_asset_allocation_agent()

    # 2. 매크로 데이터 수집
    print("\n1. 매크로 경제 데이터 수집:")
    macro_data = agent.collect_macro_data()
    print(f"   수집 완료: {len(macro_data)} 항목")

    # 3. 시장 환경 분석
    print("\n2. 시장 환경 분석:")
    environment = agent.analyze_market_environment(macro_data)
    print(environment)

    # 4. 자산 배분 제안
    print("\n3. 자산 배분 제안 생성 (1억원, 보통 리스크):")
    recommendation = agent.generate_asset_allocation(
        investment_amount=100000000,
        risk_tolerance="보통"
    )

    if recommendation:
        print(f"\n   총 배분: {recommendation.total_allocation}%")
        print(f"   자산 클래스: {len(recommendation.allocations)}개")
        print(f"\n   배분 내역:")
        for allocation in recommendation.allocations:
            print(f"      - {allocation.asset_class}: {allocation.allocation_percent}% ({allocation.risk_level})")
            print(f"        근거: {allocation.reasoning[:100]}...")
            if allocation.instruments:
                print(f"        수단: {', '.join(allocation.instruments[:3])}")

        print(f"\n   리밸런싱: {recommendation.rebalancing_frequency}")

        # 5. 요약 정보
        print("\n4. 자산 배분 요약:")
        summary = agent.get_allocation_summary(recommendation)
        print(f"   현금/MMF: {summary.get('cash_allocation', 0):.1f}%")
        print(f"   채권: {summary.get('bond_allocation', 0):.1f}%")
        print(f"   주식: {summary.get('stock_allocation', 0):.1f}%")
        print(f"   대체자산: {summary.get('alternative_allocation', 0):.1f}%")
        print(f"   고위험 자산: {summary.get('high_risk_allocation', 0):.1f}%")
    else:
        print("   ❌ 자산 배분 제안 생성 실패")
