"""포트폴리오 추적 및 거래 실행 시스템

사용자의 실제 포트폴리오를 추적하고 리밸런싱 계획을 실행
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """포지션 정보"""
    ticker: str
    shares: float
    avg_price: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class Transaction:
    """거래 내역"""
    ticker: str
    action: str  # "BUY" or "SELL"
    shares: float
    price: float
    total_value: float
    fee: float
    timestamp: datetime
    reason: str


class PortfolioTracker:
    """포트폴리오 추적기"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        logger.info(f"✅ 포트폴리오 추적기 초기화 (사용자: {user_id})")

    async def get_current_portfolio(self) -> Dict:
        """현재 포트폴리오 조회 (Supabase)"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            # 최신 포트폴리오 스냅샷 조회
            result = supabase.table("user_portfolios").select("*").eq("user_id", self.user_id).order("snapshot_date", desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                portfolio_data = result.data[0]

                # 현재 가격 업데이트
                holdings = portfolio_data.get("holdings", [])
                updated_holdings = []
                total_value = 0

                for holding in holdings:
                    ticker = holding["ticker"]
                    shares = holding["shares"]

                    # 현재 가격 조회
                    current_price = self._get_current_price(ticker)

                    if current_price > 0:
                        current_value = shares * current_price
                        avg_price = holding.get("avg_price", current_price)

                        position = {
                            "ticker": ticker,
                            "shares": shares,
                            "avg_price": avg_price,
                            "current_price": current_price,
                            "current_value": current_value,
                            "unrealized_pnl": current_value - (shares * avg_price),
                            "unrealized_pnl_pct": ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0,
                        }
                        updated_holdings.append(position)
                        total_value += current_value

                return {"portfolio_id": portfolio_data["id"], "total_value": total_value + portfolio_data.get("cash_balance", 0), "cash_balance": portfolio_data.get("cash_balance", 0), "holdings": updated_holdings, "risk_tolerance": portfolio_data.get("risk_tolerance", "보통"), "selected_scenario_id": portfolio_data.get("selected_scenario_id")}

            else:
                # 포트폴리오 없음 - 초기 상태
                return {"portfolio_id": None, "total_value": 0, "cash_balance": 0, "holdings": [], "risk_tolerance": "보통", "selected_scenario_id": None}

        except Exception as e:
            logger.error(f"❌ 포트폴리오 조회 실패: {e}")
            return None

    def _get_current_price(self, ticker: str) -> float:
        """현재 가격 조회"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")

            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            else:
                logger.warning(f"⚠️ {ticker} 가격 정보 없음")
                return 0.0

        except Exception as e:
            logger.error(f"❌ {ticker} 가격 조회 실패: {e}")
            return 0.0

    async def create_portfolio_snapshot(self, total_value: float, holdings: List[Dict], cash_balance: float = 0, scenario_id: Optional[int] = None, risk_tolerance: str = "보통") -> int:
        """포트폴리오 스냅샷 생성"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            portfolio_data = {"user_id": self.user_id, "snapshot_date": datetime.now().isoformat(), "total_value": total_value, "holdings": holdings, "cash_balance": cash_balance, "selected_scenario_id": scenario_id, "risk_tolerance": risk_tolerance}

            result = supabase.table("user_portfolios").insert(portfolio_data).execute()

            if result.data:
                portfolio_id = result.data[0]["id"]
                logger.info(f"✅ 포트폴리오 스냅샷 생성 완료 (ID: {portfolio_id})")
                return portfolio_id
            else:
                logger.error("❌ 포트폴리오 스냅샷 생성 실패")
                return 0

        except Exception as e:
            logger.error(f"❌ 포트폴리오 스냅샷 생성 오류: {e}")
            return 0

    async def execute_rebalancing_actions(self, actions: List[Dict], portfolio_id: int, scenario_id: int, dry_run: bool = True) -> List[Transaction]:
        """리밸런싱 액션 실행

        Args:
            actions: 리밸런싱 액션 리스트 (RebalancingAction 딕셔너리)
            portfolio_id: 포트폴리오 ID
            scenario_id: 시나리오 ID
            dry_run: True면 시뮬레이션만, False면 실제 거래

        Returns:
            거래 내역 리스트
        """
        transactions = []

        if dry_run:
            logger.info("🔍 시뮬레이션 모드 - 실제 거래 없음")

        for action_data in actions:
            action = action_data.get("action")
            ticker = action_data.get("ticker")
            shares_change = action_data.get("shares_change", 0)
            reason = action_data.get("reason", "")

            if action == "HOLD" or abs(shares_change) < 0.01:
                continue

            # 현재 가격 조회
            current_price = self._get_current_price(ticker)
            if current_price == 0:
                logger.warning(f"⚠️ {ticker} 가격 정보 없어 거래 스킵")
                continue

            # 거래 수량 및 금액
            shares = abs(shares_change)
            total_value = shares * current_price
            fee = total_value * 0.001  # 0.1% 수수료

            if dry_run:
                logger.info(f"📝 시뮬레이션: {action} {ticker} {shares:.2f}주 @ ${current_price:.2f} = ${total_value:,.0f}")
            else:
                # 실제 거래 실행 (브로커 API 연동 필요)
                logger.info(f"🔄 거래 실행: {action} {ticker} {shares:.2f}주 @ ${current_price:.2f}")

            # 거래 내역 기록
            transaction = Transaction(ticker=ticker, action=action, shares=shares, price=current_price, total_value=total_value, fee=fee, timestamp=datetime.now(), reason=reason)

            transactions.append(transaction)

            # Supabase에 거래 내역 저장
            await self._save_transaction_to_db(transaction, portfolio_id, scenario_id)

        return transactions

    async def _save_transaction_to_db(self, transaction: Transaction, portfolio_id: int, scenario_id: int) -> bool:
        """거래 내역을 Supabase에 저장"""
        try:
            from src.tools.supabase_rag import get_supabase_client

            supabase = get_supabase_client()

            transaction_data = {
                "user_id": self.user_id,
                "portfolio_id": portfolio_id,
                "transaction_date": transaction.timestamp.isoformat(),
                "action": transaction.action,
                "ticker": transaction.ticker,
                "shares": transaction.shares,
                "price": transaction.price,
                "total_value": transaction.total_value,
                "fee": transaction.fee,
                "reason": f"시나리오 {scenario_id} 리밸런싱: {transaction.reason}",
            }

            result = supabase.table("portfolio_transactions").insert(transaction_data).execute()

            if result.data:
                logger.info(f"✅ 거래 내역 저장 완료")
                return True
            else:
                logger.error("❌ 거래 내역 저장 실패")
                return False

        except Exception as e:
            logger.error(f"❌ 거래 내역 저장 오류: {e}")
            return False

    async def get_transaction_history(self, days: int = 30) -> List[Dict]:
        """거래 내역 조회"""
        try:
            from src.tools.supabase_rag import get_supabase_client
            from datetime import timedelta

            supabase = get_supabase_client()

            start_date = (datetime.now() - timedelta(days=days)).isoformat()

            result = supabase.table("portfolio_transactions").select("*").eq("user_id", self.user_id).gte("transaction_date", start_date).order("transaction_date", desc=True).execute()

            if result.data:
                return result.data
            else:
                return []

        except Exception as e:
            logger.error(f"❌ 거래 내역 조회 실패: {e}")
            return []


# 테스트
async def main():
    """포트폴리오 추적 테스트"""
    tracker = PortfolioTracker(user_id="test-user-001")

    # 1. 현재 포트폴리오 조회
    portfolio = await tracker.get_current_portfolio()
    print("\n" + "=" * 80)
    print("📊 현재 포트폴리오")
    print("=" * 80)
    if portfolio:
        print(f"총 가치: ${portfolio['total_value']:,.0f}")
        print(f"현금: ${portfolio['cash_balance']:,.0f}")
        print(f"보유 종목 수: {len(portfolio['holdings'])}")
    else:
        print("포트폴리오 없음 - 초기 상태")

    # 2. 샘플 리밸런싱 액션 실행 (시뮬레이션)
    sample_actions = [{"action": "BUY", "ticker": "AAPL", "shares_change": 10, "reason": "목표 비중 달성"}, {"action": "SELL", "ticker": "TSLA", "shares_change": -5, "reason": "비중 축소"}]

    print("\n" + "=" * 80)
    print("🔄 리밸런싱 시뮬레이션")
    print("=" * 80)

    transactions = await tracker.execute_rebalancing_actions(actions=sample_actions, portfolio_id=portfolio.get("portfolio_id", 0) if portfolio else 0, scenario_id=1, dry_run=True)

    for txn in transactions:
        print(f"{txn.action:4} {txn.ticker:6} {txn.shares:8.2f}주 @ ${txn.price:.2f} = ${txn.total_value:,.0f}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
