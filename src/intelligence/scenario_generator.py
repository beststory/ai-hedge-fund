"""AI 기반 투자 시나리오 생성 엔진

매크로 경제, 블로그 백테스팅, 뉴스 분석을 종합하여
3-5개의 투자 시나리오를 생성하고 확률을 계산
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import json
from pydantic import BaseModel, Field
from src.utils.llm import call_llm
from src.llm.models import ModelProvider

logger = logging.getLogger(__name__)


class AssetAllocation(BaseModel):
    """자산 배분"""
    asset_class: str = Field(description="자산 분류 (미국주식, 일본주식, 중국주식, 한국주식, ETF, 채권, 현금 등)")
    allocation_pct: float = Field(description="배분 비율 (0-100)")
    tickers: List[str] = Field(description="추천 종목 리스트")
    reasoning: str = Field(description="배분 근거")


class InvestmentScenario(BaseModel):
    """투자 시나리오"""
    scenario_name: str = Field(description="시나리오 이름")
    scenario_type: str = Field(description="유형 (낙관적, 중립적, 비관적)")
    probability: float = Field(description="발생 확률 (0-1)")
    description: str = Field(description="시나리오 설명 (2-3문장)")
    key_assumptions: List[str] = Field(description="핵심 가정 리스트")
    asset_allocations: List[AssetAllocation] = Field(description="자산 배분 제안")
    expected_return: float = Field(description="예상 수익률 (%, 6개월)")
    risk_level: str = Field(description="리스크 수준 (낮음, 보통, 높음)")
    success_probability: float = Field(description="성공 확률 (0-1)")


class MultiScenarioAnalysis(BaseModel):
    """다중 시나리오 분석 결과"""
    scenarios: List[InvestmentScenario] = Field(description="생성된 시나리오 리스트 (3-5개)")
    current_market_summary: str = Field(description="현재 시장 상황 요약")
    recommendation: str = Field(description="전체 추천 의견")


@dataclass
class EconomicSnapshot:
    """경제 상황 스냅샷"""
    gdp_growth: float
    inflation_rate: float
    unemployment_rate: float
    interest_rate: float
    vix_index: float
    news_sentiment: float
    blog_sentiment: float
    geopolitical_risk: str


class ScenarioGenerator:
    """투자 시나리오 생성 엔진"""

    def __init__(self, ai_engine: str = "ollama"):
        self.ai_engine = ai_engine
        logger.info(f"✅ 시나리오 생성 엔진 초기화 (AI: {ai_engine})")

    async def get_current_economic_snapshot(self) -> EconomicSnapshot:
        """현재 경제 상황 스냅샷 수집"""
        try:
            from src.tools.economic_indicators import get_economic_indicators
            from src.tools.news_aggregator import get_news_sentiment

            # 경제 지표 수집
            indicators = get_economic_indicators()

            # 뉴스 감성 분석
            news_sentiment = 0.0
            try:
                news_data = get_news_sentiment()
                news_sentiment = news_data.get('sentiment_score', 0.0)
            except:
                pass

            snapshot = EconomicSnapshot(
                gdp_growth=indicators.get('gdp_growth', 2.5),
                inflation_rate=indicators.get('inflation', 3.2),
                unemployment_rate=indicators.get('unemployment', 3.8),
                interest_rate=indicators.get('interest_rate', 5.25),
                vix_index=15.2,  # VIX는 별도 API 필요
                news_sentiment=news_sentiment,
                blog_sentiment=0.15,  # 블로그 감성은 RAG에서 가져올 수 있음
                geopolitical_risk="보통"
            )

            logger.info(f"✅ 경제 스냅샷 수집 완료: GDP {snapshot.gdp_growth}%, 인플레이션 {snapshot.inflation_rate}%")
            return snapshot

        except Exception as e:
            logger.warning(f"⚠️ 경제 지표 수집 실패, 기본값 사용: {e}")
            return EconomicSnapshot(
                gdp_growth=2.5,
                inflation_rate=3.2,
                unemployment_rate=3.8,
                interest_rate=5.25,
                vix_index=15.2,
                news_sentiment=0.0,
                blog_sentiment=0.0,
                geopolitical_risk="보통"
            )

    async def get_blog_backtest_insights(self, limit: int = 20) -> List[Dict]:
        """블로그 백테스팅 결과에서 인사이트 추출"""
        try:
            from src.tools.supabase_rag import SupabaseRAG

            rag = SupabaseRAG()

            # 최근 성공한 인사이트 검색
            insights = []
            keywords = ["투자", "전망", "분석", "추천", "시장"]

            for keyword in keywords:
                results = rag.search_similar(keyword, top_k=5)
                insights.extend(results)

            # 중복 제거 및 최근순 정렬
            unique_insights = {ins['id']: ins for ins in insights if 'id' in ins}
            sorted_insights = sorted(
                unique_insights.values(),
                key=lambda x: x.get('date', ''),
                reverse=True
            )[:limit]

            logger.info(f"✅ {len(sorted_insights)}개 블로그 인사이트 추출")
            return sorted_insights

        except Exception as e:
            logger.warning(f"⚠️ 블로그 인사이트 추출 실패: {e}")
            return []

    async def generate_scenarios(
        self,
        economic_snapshot: Optional[EconomicSnapshot] = None,
        num_scenarios: int = 3
    ) -> MultiScenarioAnalysis:
        """투자 시나리오 생성

        Args:
            economic_snapshot: 경제 상황 스냅샷 (없으면 자동 수집)
            num_scenarios: 생성할 시나리오 개수 (3-5개)

        Returns:
            MultiScenarioAnalysis
        """
        # 1. 경제 상황 수집
        if economic_snapshot is None:
            economic_snapshot = await self.get_current_economic_snapshot()

        # 2. 블로그 인사이트 수집
        blog_insights = await self.get_blog_backtest_insights(limit=20)

        # 3. 프롬프트 생성
        prompt = self._build_scenario_prompt(economic_snapshot, blog_insights, num_scenarios)

        # 4. AI 모델로 시나리오 생성
        logger.info("🤖 AI 모델로 투자 시나리오 생성 중...")

        try:
            result = call_llm(
                prompt=prompt,
                model_provider=ModelProvider.OLLAMA if self.ai_engine == "ollama" else ModelProvider.OPENAI,
                model_name="llama3.2" if self.ai_engine == "ollama" else "gpt-4",
                response_model=MultiScenarioAnalysis,
                temperature=0.7
            )

            logger.info(f"✅ {len(result.scenarios)}개 시나리오 생성 완료")
            return result

        except Exception as e:
            logger.error(f"❌ 시나리오 생성 실패: {e}")
            # 폴백: 기본 시나리오 반환
            return self._generate_fallback_scenarios()

    def _build_scenario_prompt(
        self,
        economic_snapshot: EconomicSnapshot,
        blog_insights: List[Dict],
        num_scenarios: int
    ) -> str:
        """시나리오 생성 프롬프트 작성"""

        # 블로그 인사이트 요약
        blog_summary = "\n".join([
            f"- {ins.get('title', '')} ({ins.get('date', '')})"
            for ins in blog_insights[:10]
        ])

        prompt = f"""당신은 세계적인 투자 전략가입니다. 현재 경제 상황과 과거 블로그 분석 결과를 바탕으로 {num_scenarios}개의 투자 시나리오를 생성해주세요.

## 현재 경제 상황
- GDP 성장률: {economic_snapshot.gdp_growth}%
- 인플레이션: {economic_snapshot.inflation_rate}%
- 실업률: {economic_snapshot.unemployment_rate}%
- 기준 금리: {economic_snapshot.interest_rate}%
- VIX 지수: {economic_snapshot.vix_index} (변동성)
- 뉴스 감성: {economic_snapshot.news_sentiment:.2f} (-1: 부정, 0: 중립, 1: 긍정)
- 블로그 분위기: {economic_snapshot.blog_sentiment:.2f}
- 지정학적 리스크: {economic_snapshot.geopolitical_risk}

## 최근 블로그 인사이트 (투자 커뮤니티 분석)
{blog_summary}

## 요구사항
1. **낙관적 시나리오** (확률 20-35%): 경제 성장 가속, 기술주 강세 등
2. **중립적 시나리오** (확률 40-60%): 현상 유지, 완만한 성장
3. **비관적 시나리오** (확률 15-30%): 경기 둔화, 금리 인상 우려 등

각 시나리오마다:
- 명확한 자산 배분 제안 (미국주식, 일본주식, 중국주식, 한국주식, ETF, 채권, 현금 등)
- 구체적인 종목 추천 (예: AAPL, 7203.T, 0700.HK, 005930.KS 등)
- 6개월 예상 수익률
- 리스크 수준 평가

**중요**: 실제 투자 가능한 현실적인 시나리오를 제시하고, 각 시나리오의 확률 합계가 100%가 되도록 해주세요.
"""

        return prompt

    def _generate_fallback_scenarios(self) -> MultiScenarioAnalysis:
        """AI 실패 시 기본 시나리오 반환"""
        logger.warning("⚠️ AI 시나리오 생성 실패, 기본 시나리오 사용")

        scenarios = [
            InvestmentScenario(
                scenario_name="기술주 중심 성장 시나리오",
                scenario_type="낙관적",
                probability=0.30,
                description="AI 및 반도체 산업 호황으로 기술주가 시장을 주도합니다. 미국과 일본 기술주 중심의 포트폴리오가 유리합니다.",
                key_assumptions=[
                    "AI 투자 지속 증가",
                    "반도체 수요 회복",
                    "금리 안정화"
                ],
                asset_allocations=[
                    AssetAllocation(
                        asset_class="미국 기술주",
                        allocation_pct=40.0,
                        tickers=["AAPL", "MSFT", "NVDA", "GOOGL"],
                        reasoning="AI 및 클라우드 성장 수혜"
                    ),
                    AssetAllocation(
                        asset_class="일본 제조업",
                        allocation_pct=20.0,
                        tickers=["7203.T", "6758.T"],
                        reasoning="엔저 수혜 및 수출 증가"
                    ),
                    AssetAllocation(
                        asset_class="중국 성장주",
                        allocation_pct=15.0,
                        tickers=["0700.HK", "9988.HK"],
                        reasoning="중국 경제 회복 기대"
                    ),
                    AssetAllocation(
                        asset_class="ETF",
                        allocation_pct=25.0,
                        tickers=["QQQ", "SMH"],
                        reasoning="분산 투자 및 리스크 관리"
                    )
                ],
                expected_return=12.0,
                risk_level="높음",
                success_probability=0.65
            ),
            InvestmentScenario(
                scenario_name="균형 성장 시나리오",
                scenario_type="중립적",
                probability=0.50,
                description="경제가 안정적으로 성장하며, 섹터 간 균형잡힌 투자가 유리합니다. 변동성이 낮고 꾸준한 수익을 추구합니다.",
                key_assumptions=[
                    "GDP 2-3% 성장 지속",
                    "인플레이션 완만한 하락",
                    "지정학적 리스크 제한적"
                ],
                asset_allocations=[
                    AssetAllocation(
                        asset_class="미국 우량주",
                        allocation_pct=30.0,
                        tickers=["AAPL", "MSFT", "JNJ", "PG"],
                        reasoning="안정적 배당 및 성장"
                    ),
                    AssetAllocation(
                        asset_class="일본 주식",
                        allocation_pct=20.0,
                        tickers=["7203.T", "6758.T", "8306.T"],
                        reasoning="저평가 및 회복 기대"
                    ),
                    AssetAllocation(
                        asset_class="중국/한국 주식",
                        allocation_pct=15.0,
                        tickers=["0700.HK", "005930.KS"],
                        reasoning="아시아 성장 참여"
                    ),
                    AssetAllocation(
                        asset_class="채권 ETF",
                        allocation_pct=20.0,
                        tickers=["AGG", "BND"],
                        reasoning="안정성 확보"
                    ),
                    AssetAllocation(
                        asset_class="현금",
                        allocation_pct=15.0,
                        tickers=[],
                        reasoning="기회 대기 및 리스크 관리"
                    )
                ],
                expected_return=6.0,
                risk_level="보통",
                success_probability=0.75
            ),
            InvestmentScenario(
                scenario_name="방어적 포지션 시나리오",
                scenario_type="비관적",
                probability=0.20,
                description="경기 둔화 우려로 방어주와 안전자산 중심의 포트폴리오를 구성합니다. 원금 보전과 배당 수익에 집중합니다.",
                key_assumptions=[
                    "경기 침체 가능성",
                    "금리 추가 인상",
                    "기업 실적 둔화"
                ],
                asset_allocations=[
                    AssetAllocation(
                        asset_class="미국 방어주",
                        allocation_pct=25.0,
                        tickers=["JNJ", "PG", "KO"],
                        reasoning="경기 방어적 섹터"
                    ),
                    AssetAllocation(
                        asset_class="채권",
                        allocation_pct=40.0,
                        tickers=["AGG", "BND", "TLT"],
                        reasoning="안전자산 선호"
                    ),
                    AssetAllocation(
                        asset_class="금 ETF",
                        allocation_pct=20.0,
                        tickers=["GLD", "IAU"],
                        reasoning="인플레이션 헤지"
                    ),
                    AssetAllocation(
                        asset_class="현금",
                        allocation_pct=15.0,
                        tickers=[],
                        reasoning="유동성 확보"
                    )
                ],
                expected_return=3.0,
                risk_level="낮음",
                success_probability=0.80
            )
        ]

        return MultiScenarioAnalysis(
            scenarios=scenarios,
            current_market_summary="현재 시장은 불확실성이 높은 상태입니다. 글로벌 경제 성장 둔화 우려와 금리 인상 압력이 공존하고 있습니다.",
            recommendation="중립적 시나리오를 기본으로 하되, 시장 상황에 따라 낙관적 또는 비관적 시나리오로 조정하는 것을 권장합니다."
        )

    async def save_scenarios_to_db(self, analysis: MultiScenarioAnalysis) -> List[int]:
        """생성된 시나리오를 Supabase에 저장"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()
            saved_ids = []

            for scenario in analysis.scenarios:
                # 시나리오 데이터 준비
                scenario_data = {
                    "scenario_name": scenario.scenario_name,
                    "scenario_type": scenario.scenario_type,
                    "probability": scenario.probability,
                    "description": scenario.description,
                    "assumptions": json.dumps(scenario.key_assumptions, ensure_ascii=False),
                    "asset_allocation": json.dumps(
                        [alloc.dict() for alloc in scenario.asset_allocations],
                        ensure_ascii=False
                    ),
                    "expected_return": scenario.expected_return,
                    "risk_level": scenario.risk_level,
                    "success_probability": scenario.success_probability,
                    "generated_at": datetime.now().isoformat(),
                    "is_active": True
                }

                # Supabase에 저장
                result = supabase.table("investment_scenarios").insert(scenario_data).execute()

                if result.data:
                    saved_id = result.data[0]['id']
                    saved_ids.append(saved_id)
                    logger.info(f"✅ 시나리오 저장 완료: {scenario.scenario_name} (ID: {saved_id})")

            logger.info(f"✅ 총 {len(saved_ids)}개 시나리오 저장 완료")
            return saved_ids

        except Exception as e:
            logger.error(f"❌ 시나리오 저장 실패: {e}")
            return []


# 테스트 실행
async def main():
    """시나리오 생성기 테스트"""
    generator = ScenarioGenerator(ai_engine="ollama")

    # 시나리오 생성
    analysis = await generator.generate_scenarios(num_scenarios=3)

    print("\n" + "="*80)
    print("🎯 AI 투자 시나리오 생성 결과")
    print("="*80)
    print(f"\n현재 시장 요약: {analysis.current_market_summary}")
    print(f"\n전체 추천: {analysis.recommendation}\n")

    for i, scenario in enumerate(analysis.scenarios, 1):
        print(f"\n{'='*80}")
        print(f"시나리오 {i}: {scenario.scenario_name} ({scenario.scenario_type})")
        print(f"{'='*80}")
        print(f"발생 확률: {scenario.probability*100:.1f}%")
        print(f"설명: {scenario.description}")
        print(f"\n핵심 가정:")
        for assumption in scenario.key_assumptions:
            print(f"  - {assumption}")
        print(f"\n자산 배분:")
        for alloc in scenario.asset_allocations:
            print(f"  {alloc.asset_class}: {alloc.allocation_pct}%")
            print(f"    종목: {', '.join(alloc.tickers)}")
            print(f"    근거: {alloc.reasoning}")
        print(f"\n예상 수익률: {scenario.expected_return}% (6개월)")
        print(f"리스크: {scenario.risk_level}")
        print(f"성공 확률: {scenario.success_probability*100:.1f}%")

    # Supabase 저장
    saved_ids = await generator.save_scenarios_to_db(analysis)
    print(f"\n✅ Supabase 저장 완료: {saved_ids}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
