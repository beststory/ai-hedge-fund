"""Alpaca 브로커 API 구현"""
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from .base import BrokerInterface, Order, Position, Account, OrderType, OrderSide, OrderStatus


class AlpacaBroker(BrokerInterface):
    """Alpaca Trading API 구현"""
    
    def __init__(self, api_key: str, secret_key: str, paper_trading: bool = True):
        super().__init__(api_key, secret_key, paper_trading=paper_trading)
        self.base_url = "https://paper-api.alpaca.markets" if paper_trading else "https://api.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json"
        }
        
    def authenticate(self) -> bool:
        """인증 확인"""
        try:
            response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_account(self) -> Account:
        """계좌 정보 조회"""
        response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"계좌 조회 실패: {response.text}")
        
        data = response.json()
        positions = self.get_positions()
        
        return Account(
            account_id=data.get("account_number", ""),
            buying_power=float(data.get("buying_power", 0)),
            total_value=float(data.get("equity", 0)),
            cash=float(data.get("cash", 0)),
            equity=float(data.get("equity", 0)),
            positions=positions
        )
    
    def get_positions(self) -> List[Position]:
        """포지션 조회"""
        response = requests.get(f"{self.base_url}/v2/positions", headers=self.headers)
        if response.status_code != 200:
            return []
        
        positions = []
        for pos_data in response.json():
            positions.append(Position(
                symbol=pos_data["symbol"],
                quantity=float(pos_data["qty"]),
                market_value=float(pos_data["market_value"]),
                cost_basis=float(pos_data["cost_basis"]),
                unrealized_pnl=float(pos_data["unrealized_pl"]),
                side="long" if float(pos_data["qty"]) > 0 else "short"
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
        order_data = {
            "symbol": symbol,
            "qty": str(abs(quantity)),
            "side": side.value,
            "type": order_type.value,
            "time_in_force": "day"
        }
        
        if order_type == OrderType.LIMIT and limit_price:
            order_data["limit_price"] = str(limit_price)
        elif order_type == OrderType.STOP and stop_price:
            order_data["stop_price"] = str(stop_price)
        elif order_type == OrderType.STOP_LIMIT and limit_price and stop_price:
            order_data["limit_price"] = str(limit_price)
            order_data["stop_price"] = str(stop_price)
        
        response = requests.post(f"{self.base_url}/v2/orders", headers=self.headers, json=order_data)
        if response.status_code not in [200, 201]:
            raise Exception(f"주문 실행 실패: {response.text}")
        
        data = response.json()
        return self._convert_alpaca_order(data)
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        response = requests.delete(f"{self.base_url}/v2/orders/{order_id}", headers=self.headers)
        return response.status_code == 204
    
    def get_order_status(self, order_id: str) -> Order:
        """주문 상태 조회"""
        response = requests.get(f"{self.base_url}/v2/orders/{order_id}", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"주문 조회 실패: {response.text}")
        
        return self._convert_alpaca_order(response.json())
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """주문 목록 조회"""
        params = {"limit": 100}
        if status:
            status_map = {
                OrderStatus.PENDING: "new",
                OrderStatus.FILLED: "filled",
                OrderStatus.CANCELLED: "cancelled",
                OrderStatus.REJECTED: "rejected"
            }
            params["status"] = status_map.get(status, "open")
        
        response = requests.get(f"{self.base_url}/v2/orders", headers=self.headers, params=params)
        if response.status_code != 200:
            return []
        
        return [self._convert_alpaca_order(order_data) for order_data in response.json()]
    
    def get_current_price(self, symbol: str) -> float:
        """현재 주가 조회"""
        response = requests.get(f"{self.base_url}/v2/stocks/{symbol}/quotes/latest", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"주가 조회 실패: {response.text}")
        
        data = response.json()
        quote = data.get("quote", {})
        return (float(quote.get("bp", 0)) + float(quote.get("ap", 0))) / 2
    
    def is_market_open(self) -> bool:
        """시장 개장 여부 확인"""
        response = requests.get(f"{self.base_url}/v2/clock", headers=self.headers)
        if response.status_code != 200:
            return False
        
        data = response.json()
        return data.get("is_open", False)
    
    def _convert_alpaca_order(self, data: Dict) -> Order:
        """Alpaca 주문 데이터를 Order 객체로 변환"""
        status_map = {
            "new": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "done_for_day": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
            "replaced": OrderStatus.CANCELLED,
            "pending_cancel": OrderStatus.PENDING,
            "pending_replace": OrderStatus.PENDING,
            "accepted": OrderStatus.PENDING,
            "pending_new": OrderStatus.PENDING,
            "accepted_for_bidding": OrderStatus.PENDING,
            "stopped": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "suspended": OrderStatus.CANCELLED
        }
        
        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT
        }
        
        side_map = {
            "buy": OrderSide.BUY,
            "sell": OrderSide.SELL
        }
        
        created_at = None
        filled_at = None
        
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        
        if data.get("filled_at"):
            filled_at = datetime.fromisoformat(data["filled_at"].replace("Z", "+00:00"))
        
        return Order(
            order_id=data["id"],
            symbol=data["symbol"],
            quantity=float(data["qty"]),
            side=side_map.get(data["side"], OrderSide.BUY),
            order_type=order_type_map.get(data["type"], OrderType.MARKET),
            limit_price=float(data["limit_price"]) if data.get("limit_price") else None,
            stop_price=float(data["stop_price"]) if data.get("stop_price") else None,
            filled_quantity=float(data.get("filled_qty", 0)),
            status=status_map.get(data["status"], OrderStatus.PENDING),
            created_at=created_at,
            filled_at=filled_at
        )