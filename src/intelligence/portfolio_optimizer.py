"""자산 배분 최적화 및 리밸런싱 시스템

사용자 포트폴리오와 선택한 시나리오를 기반으로
최적의 자산 배분을 계산하고 리밸런싱 계획을 제시
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from pydantic import BaseModel, Field
import yfinance as yf

logger = logging.getLogger(__name__)


class Holding(BaseModel):
    """보유 종목"""
    ticker: str
    shares: float
    avg_price: float
    current_price: float
    current_value: float
    weight_pct: float


class UserPortfolio(BaseModel):
    """사용자 포트폴리오"""
    total_value: float
    cash_balance: float
    holdings: List[Holding]
    risk_tolerance: str  # "낮음", "보통", "높음"


class RebalancingAction(BaseModel):
    """리밸런싱 액션"""
    action: str  # "BUY", "SELL", "HOLD"
    ticker: str
    current_shares: float
    target_shares: float
    shares_change: float
    estimated_cost: float
    reason: str


class RebalancingPlan(BaseModel):
    """리밸런싱 계획"""
    current_allocation: Dict[str, float]  # {ticker: weight%}
    target_allocation: Dict[str, float]
    actions: List[RebalancingAction]
    estimated_total_cost: float
    estimated_new_value: float
    rebalancing_summary: str


@dataclass
class ScenarioAllocation:
    """시나리오 자산 배분"""
    asset_class: str
    allocation_pct: float
    tickers: List[str]
    reasoning: str


class PortfolioOptimizer:
    """포트폴리오 최적화 엔진"""

    def __init__(self):
        logger.info("✅ 포트폴리오 최적화 엔진 초기화")

    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """현재 가격 조회"""
        prices = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")

                if not hist.empty:
                    prices[ticker] = float(hist['Close'].iloc[-1])
                else:
                    logger.warning(f"⚠️ {ticker} 가격 정보 없음")
                    prices[ticker] = 0.0

            except Exception as e:
                logger.error(f"❌ {ticker} 가격 조회 실패: {e}")
                prices[ticker] = 0.0

        return prices

    def calculate_portfolio_value(self, portfolio: UserPortfolio) -> float:
        """포트폴리오 총 가치 계산"""
        holdings_value = sum(h.current_value for h in portfolio.holdings)
        return holdings_value + portfolio.cash_balance

    def parse_scenario_allocations(self, scenario_data: Dict) -> List[ScenarioAllocation]:
        """시나리오에서 자산 배분 추출"""
        allocations = []

        asset_allocation = scenario_data.get('asset_allocation', [])

        for alloc in asset_allocation:
            allocations.append(ScenarioAllocation(
                asset_class=alloc.get('asset_class', ''),
                allocation_pct=alloc.get('allocation_pct', 0.0),
                tickers=alloc.get('tickers', []),
                reasoning=alloc.get('reasoning', '')
            ))

        return allocations

    def generate_rebalancing_plan(
        self,
        current_portfolio: UserPortfolio,
        scenario_allocations: List[ScenarioAllocation],
        total_investment: Optional[float] = None
    ) -> RebalancingPlan:
        """리밸런싱 계획 생성

        Args:
            current_portfolio: 현재 포트폴리오
            scenario_allocations: 목표 자산 배분 (시나리오에서 추출)
            total_investment: 총 투자 금액 (없으면 현재 포트폴리오 가치 사용)

        Returns:
            RebalancingPlan
        """
        # 1. 총 투자 금액 설정
        if total_investment is None:
            total_investment = self.calculate_portfolio_value(current_portfolio)

        # 2. 목표 배분 계산
        target_allocation = self._calculate_target_allocation(
            scenario_allocations,
            total_investment
        )

        # 3. 현재 배분 계산
        current_allocation = self._calculate_current_allocation(current_portfolio)

        # 4. 현재 가격 조회
        all_tickers = list(set(
            list(current_allocation.keys()) +
            list(target_allocation.keys())
        ))
        current_prices = self.get_current_prices(all_tickers)

        # 5. 리밸런싱 액션 생성
        actions = self._generate_rebalancing_actions(
            current_portfolio,
            current_allocation,
            target_allocation,
            current_prices,
            total_investment
        )

        # 6. 비용 계산
        estimated_total_cost = sum(
            abs(action.estimated_cost) for action in actions
            if action.action in ['BUY', 'SELL']
        )

        # 7. 요약 생성
        summary = self._generate_rebalancing_summary(actions, current_allocation, target_allocation)

        return RebalancingPlan(
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            actions=actions,
            estimated_total_cost=estimated_total_cost,
            estimated_new_value=total_investment,
            rebalancing_summary=summary
        )

    def _calculate_target_allocation(
        self,
        scenario_allocations: List[ScenarioAllocation],
        total_investment: float
    ) -> Dict[str, float]:
        """목표 자산 배분 계산 (종목별 가중치)"""
        target_allocation = {}

        for alloc in scenario_allocations:
            # 각 자산 클래스의 비중을 종목 수로 나눔
            if alloc.tickers:
                weight_per_ticker = alloc.allocation_pct / len(alloc.tickers)

                for ticker in alloc.tickers:
                    if ticker:  # 빈 문자열 제외
                        target_allocation[ticker] = weight_per_ticker

        # 현금 비중 추가
        total_allocated = sum(target_allocation.values())
        if total_allocated < 100:
            target_allocation['CASH'] = 100 - total_allocated

        return target_allocation

    def _calculate_current_allocation(self, portfolio: UserPortfolio) -> Dict[str, float]:
        """현재 자산 배분 계산"""
        current_allocation = {}
        total_value = self.calculate_portfolio_value(portfolio)

        if total_value == 0:
            return {'CASH': 100.0}

        for holding in portfolio.holdings:
            weight = (holding.current_value / total_value) * 100
            current_allocation[holding.ticker] = weight

        # 현금 비중
        if portfolio.cash_balance > 0:
            cash_weight = (portfolio.cash_balance / total_value) * 100
            current_allocation['CASH'] = cash_weight

        return current_allocation

    def _generate_rebalancing_actions(
        self,
        current_portfolio: UserPortfolio,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        current_prices: Dict[str, float],
        total_investment: float
    ) -> List[RebalancingAction]:
        """리밸런싱 액션 생성"""
        actions = []

        # 현재 보유 종목 맵
        current_holdings = {h.ticker: h for h in current_portfolio.holdings}

        # 모든 종목에 대해 액션 생성
        all_tickers = set(list(current_allocation.keys()) + list(target_allocation.keys()))

        for ticker in all_tickers:
            if ticker == 'CASH':
                continue

            current_weight = current_allocation.get(ticker, 0.0)
            target_weight = target_allocation.get(ticker, 0.0)
            weight_diff = target_weight - current_weight

            # 현재 주식 수
            current_shares = current_holdings.get(ticker, Holding(
                ticker=ticker, shares=0, avg_price=0, current_price=0, current_value=0, weight_pct=0
            )).shares

            # 목표 가치
            target_value = (target_weight / 100) * total_investment

            # 현재 가격
            price = current_prices.get(ticker, 0.0)
            if price == 0:
                logger.warning(f"⚠️ {ticker} 가격 정보 없음, 액션 생성 스킵")
                continue

            # 목표 주식 수
            target_shares = target_value / price

            # 주식 수 변화
            shares_change = target_shares - current_shares

            # 액션 결정
            if abs(shares_change) < 0.01:  # 거의 변화 없음
                action = "HOLD"
                reason = "현재 배분이 목표와 유사"
            elif shares_change > 0:
                action = "BUY"
                reason = f"목표 비중 {target_weight:.1f}% 달성을 위해 매수"
            else:
                action = "SELL"
                reason = f"목표 비중 {target_weight:.1f}% 달성을 위해 매도"

            # 예상 비용
            estimated_cost = abs(shares_change) * price

            actions.append(RebalancingAction(
                action=action,
                ticker=ticker,
                current_shares=float(current_shares),
                target_shares=float(target_shares),
                shares_change=float(shares_change),
                estimated_cost=float(estimated_cost),
                reason=reason
            ))

        # 액션 정렬: SELL -> BUY 순서
        actions.sort(key=lambda x: (x.action != 'SELL', x.action != 'BUY', x.ticker))

        return actions

    def _generate_rebalancing_summary(
        self,
        actions: List[RebalancingAction],
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float]
    ) -> str:
        """리밸런싱 요약 생성"""
        buy_count = sum(1 for a in actions if a.action == 'BUY')
        sell_count = sum(1 for a in actions if a.action == 'SELL')
        hold_count = sum(1 for a in actions if a.action == 'HOLD')

        summary = f"""
리밸런싱 개요:
- 매수: {buy_count}개 종목
- 매도: {sell_count}개 종목
- 유지: {hold_count}개 종목

주요 변경사항:
"""

        # 큰 변화가 있는 종목만 표시
        for action in actions:
            if action.action in ['BUY', 'SELL']:
                current_weight = current_allocation.get(action.ticker, 0.0)
                target_weight = target_allocation.get(action.ticker, 0.0)
                summary += f"- {action.ticker}: {current_weight:.1f}% → {target_weight:.1f}% ({action.action})\n"

        return summary.strip()

    async def save_rebalancing_plan_to_db(
        self,
        user_id: str,
        scenario_id: int,
        plan: RebalancingPlan,
        current_portfolio: UserPortfolio,
        total_investment: float
    ) -> int:
        """리밸런싱 계획을 Supabase에 저장"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            # 데이터 준비
            plan_data = {
                "user_id": user_id,
                "scenario_id": scenario_id,
                "proposed_date": datetime.now().isoformat(),
                "proposed_allocation": plan.target_allocation,
                "current_allocation": plan.current_allocation,
                "rebalancing_plan": [action.dict() for action in plan.actions],
                "implemented": False,
                "total_investment": total_investment
            }

            # Supabase에 저장
            result = supabase.table("asset_allocation_history").insert(plan_data).execute()

            if result.data:
                plan_id = result.data[0]['id']
                logger.info(f"✅ 리밸런싱 계획 저장 완료 (ID: {plan_id})")
                return plan_id
            else:
                logger.error("❌ 리밸런싱 계획 저장 실패")
                return 0

        except Exception as e:
            logger.error(f"❌ 리밸런싱 계획 저장 오류: {e}")
            return 0


# 테스트
async def main():
    """포트폴리오 최적화 테스트"""
    optimizer = PortfolioOptimizer()

    # 샘플 현재 포트폴리오
    current_portfolio = UserPortfolio(
        total_value=10000000,  # 1천만원
        cash_balance=2000000,  # 200만원
        holdings=[
            Holding(ticker="AAPL", shares=10, avg_price=150, current_price=180, current_value=1800000, weight_pct=18),
            Holding(ticker="TSLA", shares=15, avg_price=200, current_price=250, current_value=3750000, weight_pct=37.5),
            Holding(ticker="005930.KS", shares=50, avg_price=70000, current_price=72000, current_value=3600000, weight_pct=36),
        ],
        risk_tolerance="보통"
    )

    # 샘플 시나리오 배분
    scenario_allocations = [
        ScenarioAllocation(
            asset_class="미국 기술주",
            allocation_pct=40.0,
            tickers=["AAPL", "MSFT", "NVDA", "GOOGL"],
            reasoning="AI 성장 수혜"
        ),
        ScenarioAllocation(
            asset_class="일본 제조업",
            allocation_pct=20.0,
            tickers=["7203.T", "6758.T"],
            reasoning="엔저 수혜"
        ),
        ScenarioAllocation(
            asset_class="ETF",
            allocation_pct=25.0,
            tickers=["QQQ", "SMH"],
            reasoning="분산 투자"
        ),
        ScenarioAllocation(
            asset_class="현금",
            allocation_pct=15.0,
            tickers=[],
            reasoning="유동성 확보"
        )
    ]

    # 리밸런싱 계획 생성
    plan = optimizer.generate_rebalancing_plan(
        current_portfolio=current_portfolio,
        scenario_allocations=scenario_allocations,
        total_investment=10000000
    )

    print("\n" + "="*80)
    print("🎯 리밸런싱 계획")
    print("="*80)
    print(f"\n{plan.rebalancing_summary}\n")

    print("현재 배분:")
    for ticker, weight in sorted(plan.current_allocation.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ticker:12} : {weight:6.2f}%")

    print("\n목표 배분:")
    for ticker, weight in sorted(plan.target_allocation.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ticker:12} : {weight:6.2f}%")

    print(f"\n예상 거래 비용: ${plan.estimated_total_cost:,.0f}")

    print("\n액션 목록:")
    for action in plan.actions:
        if action.action != 'HOLD':
            print(f"  {action.action:4} {action.ticker:12} | "
                  f"현재: {action.current_shares:8.2f}주 → 목표: {action.target_shares:8.2f}주 | "
                  f"비용: ${action.estimated_cost:,.0f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
