"""Interactive Brokers API 구현"""
import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from .base import BrokerInterface, Order, Position, Account, OrderType, OrderSide, OrderStatus

try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder, util
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False


class InteractiveBrokersBroker(BrokerInterface):
    """Interactive Brokers API 구현"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", paper_trading: bool = True, host: str = "127.0.0.1", port: int = 7497):
        super().__init__(api_key, secret_key, paper_trading=paper_trading)
        
        if not IB_AVAILABLE:
            raise ImportError("ib_insync 패키지가 필요합니다. pip install ib_insync로 설치하세요.")
        
        self.host = host
        self.port = port  # 7497 for paper trading, 7496 for live
        self.ib = IB()
        self._connected = False
        
    def authenticate(self) -> bool:
        """TWS/Gateway 연결"""
        try:
            if not self._connected:
                self.ib.connect(self.host, self.port, clientId=1)
                self._connected = True
            return self.ib.isConnected()
        except Exception as e:
            print(f"IB 연결 실패: {e}")
            return False
    
    def get_account(self) -> Account:
        """계좌 정보 조회"""
        if not self._connected:
            self.authenticate()
        
        account_values = self.ib.accountValues()
        positions = self.get_positions()
        
        # 계좌 정보 추출
        buying_power = 0
        total_value = 0
        cash = 0
        equity = 0
        
        for item in account_values:
            if item.tag == "BuyingPower":
                buying_power = float(item.value)
            elif item.tag == "NetLiquidation":
                total_value = float(item.value)
                equity = float(item.value)
            elif item.tag == "AvailableFunds":
                cash = float(item.value)
        
        return Account(
            account_id=self.ib.managedAccounts()[0] if self.ib.managedAccounts() else "",
            buying_power=buying_power,
            total_value=total_value,
            cash=cash,
            equity=equity,
            positions=positions
        )
    
    def get_positions(self) -> List[Position]:
        """포지션 조회"""
        if not self._connected:
            self.authenticate()
        
        positions = []
        for pos in self.ib.positions():
            if pos.position != 0:  # 포지션이 있는 경우만
                positions.append(Position(
                    symbol=pos.contract.symbol,
                    quantity=float(pos.position),
                    market_value=float(pos.marketValue),
                    cost_basis=float(pos.averageCost * abs(pos.position)),
                    unrealized_pnl=float(pos.unrealizedPNL),
                    side="long" if pos.position > 0 else "short"
                ))
        
        return positions
    
    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """주문 실행"""
        if not self._connected:
            self.authenticate()
        
        # 계약 생성
        contract = Stock(symbol, 'SMART', 'USD')
        
        # 주문 수량 (IB는 buy/sell을 수량의 부호로 구분)
        ib_quantity = abs(quantity) if side == OrderSide.BUY else -abs(quantity)
        
        # 주문 타입에 따른 주문 객체 생성
        if order_type == OrderType.MARKET:
            ib_order = MarketOrder(side.value.upper(), abs(quantity))
        elif order_type == OrderType.LIMIT and limit_price:
            ib_order = LimitOrder(side.value.upper(), abs(quantity), limit_price)
        elif order_type == OrderType.STOP and stop_price:
            ib_order = StopOrder(side.value.upper(), abs(quantity), stop_price)
        else:
            raise ValueError(f"지원하지 않는 주문 타입: {order_type}")
        
        # 주문 실행
        trade = self.ib.placeOrder(contract, ib_order)
        
        return Order(
            order_id=str(trade.order.orderId),
            symbol=symbol,
            quantity=abs(quantity),
            side=side,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            filled_quantity=0,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if not self._connected:
            self.authenticate()
        
        try:
            trades = self.ib.trades()
            for trade in trades:
                if str(trade.order.orderId) == order_id:
                    self.ib.cancelOrder(trade.order)
                    return True
            return False
        except Exception:
            return False
    
    def get_order_status(self, order_id: str) -> Order:
        """주문 상태 조회"""
        if not self._connected:
            self.authenticate()
        
        trades = self.ib.trades()
        for trade in trades:
            if str(trade.order.orderId) == order_id:
                return self._convert_ib_order(trade)
        
        raise Exception(f"주문을 찾을 수 없습니다: {order_id}")
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """주문 목록 조회"""
        if not self._connected:
            self.authenticate()
        
        orders = []
        trades = self.ib.trades()
        
        for trade in trades:
            order = self._convert_ib_order(trade)
            if status is None or order.status == status:
                orders.append(order)
        
        return orders
    
    def get_current_price(self, symbol: str) -> float:
        """현재 주가 조회"""
        if not self._connected:
            self.authenticate()
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        # 실시간 데이터 요청
        ticker = self.ib.reqMktData(contract)
        
        # 데이터가 올 때까지 대기
        for _ in range(30):  # 3초 대기
            self.ib.sleep(0.1)
            if ticker.marketPrice():
                price = ticker.marketPrice()
                self.ib.cancelMktData(contract)
                return float(price)
        
        # 실시간 데이터가 없으면 마지막 거래가 사용
        if ticker.last:
            return float(ticker.last)
        
        raise Exception(f"{symbol}의 주가를 가져올 수 없습니다")
    
    def is_market_open(self) -> bool:
        """시장 개장 여부 확인"""
        # 간단한 시간 기반 체크 (미국 동부 시간 9:30-16:00)
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone(timedelta(hours=-5)))  # EST
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # 주말 제외
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return market_open <= now <= market_close
    
    def _convert_ib_order(self, trade) -> Order:
        """IB Trade 객체를 Order 객체로 변환"""
        order = trade.order
        order_status = trade.orderStatus
        
        # 상태 변환
        status_map = {
            'PendingSubmit': OrderStatus.PENDING,
            'PendingCancel': OrderStatus.PENDING,
            'PreSubmitted': OrderStatus.PENDING,
            'Submitted': OrderStatus.PENDING,
            'Filled': OrderStatus.FILLED,
            'Cancelled': OrderStatus.CANCELLED,
            'Rejected': OrderStatus.REJECTED,
            'Inactive': OrderStatus.CANCELLED
        }
        
        # 주문 타입 변환
        order_type_map = {
            'MKT': OrderType.MARKET,
            'LMT': OrderType.LIMIT,
            'STP': OrderType.STOP,
            'STP LMT': OrderType.STOP_LIMIT
        }
        
        return Order(
            order_id=str(order.orderId),
            symbol=trade.contract.symbol,
            quantity=float(abs(order.totalQuantity)),
            side=OrderSide.BUY if order.action == 'BUY' else OrderSide.SELL,
            order_type=order_type_map.get(order.orderType, OrderType.MARKET),
            limit_price=float(order.lmtPrice) if order.lmtPrice else None,
            stop_price=float(order.auxPrice) if order.auxPrice else None,
            filled_quantity=float(order_status.filled),
            status=status_map.get(order_status.status, OrderStatus.PENDING),
            created_at=datetime.now()  # IB에서 정확한 생성 시간을 얻기 어려움
        )
    
    def disconnect(self):
        """연결 종료"""
        if self._connected:
            self.ib.disconnect()
            self._connected = False