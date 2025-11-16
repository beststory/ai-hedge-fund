"""브로커 API 기본 인터페이스"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """주문 방향"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    side: str  # "long" 또는 "short"


@dataclass
class Order:
    """주문 정보"""
    order_id: str
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class Account:
    """계좌 정보"""
    account_id: str
    buying_power: float
    total_value: float
    cash: float
    equity: float
    positions: List[Position]


class BrokerInterface(ABC):
    """브로커 API 기본 인터페이스"""
    
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        self.api_key = api_key
        self.secret_key = secret_key
        self.is_paper_trading = kwargs.get('paper_trading', True)
        
    @abstractmethod
    def authenticate(self) -> bool:
        """인증"""
        pass
    
    @abstractmethod
    def get_account(self) -> Account:
        """계좌 정보 조회"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """포지션 조회"""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """주문 상태 조회"""
        pass
    
    @abstractmethod
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """주문 목록 조회"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """현재 주가 조회"""
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """시장 개장 여부 확인"""
        pass