"""성과 분석 및 AI 학습 엔진

실제 투자 결과를 분석하고 AI 모델 가중치를 자동으로 조정
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PerformanceMetrics(BaseModel):
    """성과 지표"""
    total_return_pct: float = Field(description="총 수익률 (%)")
    annualized_return_pct: float = Field(description="연간 수익률 (%)")
    volatility: float = Field(description="변동성 (%)")
    sharpe_ratio: float = Field(description="샤프 비율")
    max_drawdown_pct: float = Field(description="최대 낙폭 (%)")
    win_rate: float = Field(description="승률 (0-1)")


class ScenarioPerformance(BaseModel):
    """시나리오 성과 분석"""
    scenario_id: int
    scenario_name: str
    selection_date: datetime
    evaluation_date: datetime
    days_elapsed: int
    expected_return: float
    actual_return: float
    accuracy_score: float  # 0-1
    success: bool
    metrics: PerformanceMetrics
    lessons_learned: str


class AILearningInsight(BaseModel):
    """AI 학습 인사이트"""
    keyword: str
    category: str  # "블로그", "뉴스", "경제지표"
    old_weight: float
    new_weight: float
    confidence: float
    reason: str


class PerformanceAnalyzer:
    """성과 분석 및 학습 엔진"""

    def __init__(self):
        logger.info("✅ 성과 분석 엔진 초기화")

    async def analyze_scenario_performance(
        self,
        scenario_id: int,
        user_id: str,
        selection_date: datetime,
        days_to_evaluate: int = 90
    ) -> Optional[ScenarioPerformance]:
        """시나리오 성과 분석

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            selection_date: 시나리오 선택 날짜
            days_to_evaluate: 평가 기간 (일)

        Returns:
            ScenarioPerformance
        """
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            # 1. 시나리오 정보 조회
            scenario_result = supabase.table("investment_scenarios").select("*").eq("id", scenario_id).execute()

            if not scenario_result.data:
                logger.error(f"❌ 시나리오 {scenario_id} 없음")
                return None

            scenario = scenario_result.data[0]

            # 2. 사용자 포트폴리오 히스토리 조회
            portfolio_history = await self._get_portfolio_history(
                user_id=user_id,
                start_date=selection_date,
                days=days_to_evaluate
            )

            if not portfolio_history:
                logger.warning(f"⚠️ 포트폴리오 히스토리 없음")
                return None

            # 3. 성과 계산
            metrics = self._calculate_performance_metrics(portfolio_history)

            # 4. 예측 vs 실제 비교
            expected_return = scenario.get('expected_return', 0.0)
            actual_return = metrics.total_return_pct

            # 정확도 계산 (오차율 기반)
            error_pct = abs(expected_return - actual_return) / max(abs(expected_return), 1.0)
            accuracy_score = max(0.0, 1.0 - error_pct)

            # 성공 여부 (실제 수익률이 예상의 80% 이상)
            success = (actual_return >= expected_return * 0.8)

            # 5. 교훈 추출
            lessons = self._extract_lessons(scenario, metrics, expected_return, actual_return)

            evaluation_date = selection_date + timedelta(days=days_to_evaluate)

            performance = ScenarioPerformance(
                scenario_id=scenario_id,
                scenario_name=scenario.get('scenario_name', ''),
                selection_date=selection_date,
                evaluation_date=evaluation_date,
                days_elapsed=days_to_evaluate,
                expected_return=expected_return,
                actual_return=actual_return,
                accuracy_score=accuracy_score,
                success=success,
                metrics=metrics,
                lessons_learned=lessons
            )

            logger.info(f"✅ 시나리오 {scenario_id} 성과 분석 완료: 예상 {expected_return:.2f}% → 실제 {actual_return:.2f}%")

            return performance

        except Exception as e:
            logger.error(f"❌ 성과 분석 실패: {e}")
            return None

    async def _get_portfolio_history(
        self,
        user_id: str,
        start_date: datetime,
        days: int
    ) -> List[Dict]:
        """포트폴리오 히스토리 조회"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            end_date = start_date + timedelta(days=days)

            result = supabase.table("user_portfolios") \
                .select("*") \
                .eq("user_id", user_id) \
                .gte("snapshot_date", start_date.isoformat()) \
                .lte("snapshot_date", end_date.isoformat()) \
                .order("snapshot_date") \
                .execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"❌ 포트폴리오 히스토리 조회 실패: {e}")
            return []

    def _calculate_performance_metrics(self, portfolio_history: List[Dict]) -> PerformanceMetrics:
        """성과 지표 계산"""
        if not portfolio_history or len(portfolio_history) < 2:
            return PerformanceMetrics(
                total_return_pct=0.0,
                annualized_return_pct=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                win_rate=0.0
            )

        # 포트폴리오 가치 시계열
        values = [p.get('total_value', 0) for p in portfolio_history]
        dates = [datetime.fromisoformat(p.get('snapshot_date', '')) for p in portfolio_history]

        # 수익률 계산
        initial_value = values[0]
        final_value = values[-1]
        total_return_pct = ((final_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0.0

        # 연간 수익률 (단순화)
        days_elapsed = (dates[-1] - dates[0]).days
        annualized_return_pct = (total_return_pct / days_elapsed) * 365 if days_elapsed > 0 else 0.0

        # 일별 수익률
        daily_returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                daily_return = (values[i] - values[i-1]) / values[i-1]
                daily_returns.append(daily_return)

        # 변동성 (연간화)
        if daily_returns:
            volatility = np.std(daily_returns) * np.sqrt(252) * 100
        else:
            volatility = 0.0

        # 샤프 비율 (무위험 수익률 3% 가정)
        risk_free_rate = 0.03
        if volatility > 0:
            sharpe_ratio = (annualized_return_pct / 100 - risk_free_rate) / (volatility / 100)
        else:
            sharpe_ratio = 0.0

        # 최대 낙폭 (MDD)
        max_drawdown_pct = 0.0
        peak = values[0]
        for value in values:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100 if peak > 0 else 0
            max_drawdown_pct = max(max_drawdown_pct, drawdown)

        # 승률 (양수 수익률 비율)
        if daily_returns:
            wins = sum(1 for r in daily_returns if r > 0)
            win_rate = wins / len(daily_returns)
        else:
            win_rate = 0.0

        return PerformanceMetrics(
            total_return_pct=round(total_return_pct, 2),
            annualized_return_pct=round(annualized_return_pct, 2),
            volatility=round(volatility, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            win_rate=round(win_rate, 2)
        )

    def _extract_lessons(
        self,
        scenario: Dict,
        metrics: PerformanceMetrics,
        expected_return: float,
        actual_return: float
    ) -> str:
        """교훈 추출"""
        lessons = []

        # 1. 예측 정확도
        if abs(actual_return - expected_return) < 2.0:
            lessons.append("✅ 수익률 예측이 매우 정확했습니다.")
        elif actual_return > expected_return:
            lessons.append(f"✅ 예상보다 높은 수익률 달성 (+{actual_return - expected_return:.2f}%p)")
        else:
            lessons.append(f"⚠️ 예상보다 낮은 수익률 ({actual_return - expected_return:.2f}%p)")

        # 2. 리스크 분석
        if metrics.volatility < 10:
            lessons.append("✅ 변동성이 낮아 안정적인 투자였습니다.")
        elif metrics.volatility > 20:
            lessons.append(f"⚠️ 높은 변동성 ({metrics.volatility:.1f}%)이 관찰되었습니다.")

        # 3. 최대 낙폭
        if metrics.max_drawdown_pct < 5:
            lessons.append("✅ 낙폭이 작아 리스크 관리가 잘 되었습니다.")
        elif metrics.max_drawdown_pct > 15:
            lessons.append(f"⚠️ 큰 낙폭 ({metrics.max_drawdown_pct:.1f}%)이 발생했습니다.")

        # 4. 샤프 비율
        if metrics.sharpe_ratio > 1.5:
            lessons.append(f"✅ 우수한 위험 대비 수익률 (샤프 {metrics.sharpe_ratio:.2f})")
        elif metrics.sharpe_ratio < 0.5:
            lessons.append(f"⚠️ 낮은 위험 대비 수익률 (샤프 {metrics.sharpe_ratio:.2f})")

        return " ".join(lessons)

    async def update_ai_model_weights(
        self,
        performance: ScenarioPerformance
    ) -> List[AILearningInsight]:
        """AI 모델 가중치 자동 조정"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()
            insights = []

            # 1. 시나리오에서 키워드 추출
            scenario_result = supabase.table("investment_scenarios") \
                .select("*") \
                .eq("id", performance.scenario_id) \
                .execute()

            if not scenario_result.data:
                return insights

            scenario = scenario_result.data[0]

            # 2. 키워드 추출 (시나리오 이름, 설명에서)
            text = f"{scenario.get('scenario_name', '')} {scenario.get('description', '')}"
            keywords = self._extract_keywords_from_text(text)

            # 3. 각 키워드에 대해 가중치 조정
            impact = 0.1 if performance.success else -0.1
            impact *= performance.accuracy_score  # 정확도에 비례

            for keyword in keywords:
                # 현재 가중치 조회
                weight_result = supabase.table("ai_model_weights") \
                    .select("*") \
                    .eq("keyword", keyword) \
                    .eq("category", "블로그") \
                    .execute()

                old_weight = 0.5  # 기본값

                if weight_result.data:
                    old_weight = weight_result.data[0].get('weight', 0.5)

                # 새 가중치 계산
                new_weight = max(0.0, min(1.0, old_weight + impact))

                # Confidence 계산 (중심에서의 거리)
                confidence = abs(new_weight - 0.5) * 2

                # 가중치 업데이트
                reason = f"시나리오 {performance.scenario_id} {'성공' if performance.success else '실패'} ({performance.accuracy_score:.2f})"

                # Supabase 함수 호출
                supabase.rpc(
                    'update_ai_weight',
                    {
                        'p_keyword': keyword,
                        'p_category': '블로그',
                        'p_success': performance.success,
                        'p_impact': abs(impact)
                    }
                ).execute()

                insight = AILearningInsight(
                    keyword=keyword,
                    category="블로그",
                    old_weight=old_weight,
                    new_weight=new_weight,
                    confidence=confidence,
                    reason=reason
                )

                insights.append(insight)

                logger.info(f"✅ AI 가중치 업데이트: {keyword} ({old_weight:.3f} → {new_weight:.3f})")

            return insights

        except Exception as e:
            logger.error(f"❌ AI 모델 가중치 업데이트 실패: {e}")
            return []

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 투자 관련 키워드 추출"""
        keywords = [
            "반도체", "AI", "인공지능", "전기차", "배터리", "바이오",
            "금리", "인플레이션", "GDP", "성장주", "가치주",
            "미국", "중국", "일본", "한국",
            "기술주", "금융주", "제조업", "에너지"
        ]

        found = []
        text_lower = text.lower()

        for keyword in keywords:
            if keyword.lower() in text_lower or keyword in text:
                found.append(keyword)

        return found[:5]  # 상위 5개만

    async def save_performance_to_db(
        self,
        performance: ScenarioPerformance,
        user_id: str
    ) -> int:
        """성과 분석 결과를 Supabase에 저장"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            data = {
                "scenario_id": performance.scenario_id,
                "user_id": user_id,
                "selection_date": performance.selection_date.isoformat(),
                "evaluation_date": performance.evaluation_date.isoformat(),
                "expected_return": performance.expected_return,
                "actual_return": performance.actual_return,
                "accuracy_score": performance.accuracy_score,
                "success": performance.success,
                "max_drawdown": performance.metrics.max_drawdown_pct,
                "volatility": performance.metrics.volatility,
                "sharpe_ratio": performance.metrics.sharpe_ratio,
                "lessons_learned": performance.lessons_learned
            }

            result = supabase.table("scenario_performance").insert(data).execute()

            if result.data:
                performance_id = result.data[0]['id']
                logger.info(f"✅ 성과 분석 저장 완료 (ID: {performance_id})")
                return performance_id
            else:
                logger.error("❌ 성과 분석 저장 실패")
                return 0

        except Exception as e:
            logger.error(f"❌ 성과 분석 저장 오류: {e}")
            return 0


# 테스트
async def main():
    """성과 분석 테스트"""
    analyzer = PerformanceAnalyzer()

    # 샘플 시나리오 성과 분석
    performance = await analyzer.analyze_scenario_performance(
        scenario_id=1,
        user_id="test-user-123",
        selection_date=datetime.now() - timedelta(days=90),
        days_to_evaluate=90
    )

    if performance:
        print("\n" + "="*80)
        print("📊 시나리오 성과 분석 결과")
        print("="*80)
        print(f"\n시나리오: {performance.scenario_name}")
        print(f"기간: {performance.selection_date.strftime('%Y-%m-%d')} ~ {performance.evaluation_date.strftime('%Y-%m-%d')} ({performance.days_elapsed}일)")
        print(f"\n예상 수익률: {performance.expected_return:.2f}%")
        print(f"실제 수익률: {performance.actual_return:.2f}%")
        print(f"정확도: {performance.accuracy_score*100:.1f}%")
        print(f"성공 여부: {'✅ 성공' if performance.success else '❌ 실패'}")

        print(f"\n성과 지표:")
        print(f"  총 수익률: {performance.metrics.total_return_pct:.2f}%")
        print(f"  연간 수익률: {performance.metrics.annualized_return_pct:.2f}%")
        print(f"  변동성: {performance.metrics.volatility:.2f}%")
        print(f"  샤프 비율: {performance.metrics.sharpe_ratio:.2f}")
        print(f"  최대 낙폭: {performance.metrics.max_drawdown_pct:.2f}%")
        print(f"  승률: {performance.metrics.win_rate*100:.1f}%")

        print(f"\n교훈: {performance.lessons_learned}")

        # AI 학습
        insights = await analyzer.update_ai_model_weights(performance)

        if insights:
            print(f"\n🤖 AI 학습 결과 ({len(insights)}개 키워드 업데이트):")
            for insight in insights:
                print(f"  {insight.keyword}: {insight.old_weight:.3f} → {insight.new_weight:.3f} (신뢰도: {insight.confidence:.3f})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
