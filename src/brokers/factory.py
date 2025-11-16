"""브로커 팩토리"""
import os
from typing import Dict, Type, Optional, List
from .base import BrokerInterface
from .alpaca_broker import AlpacaBroker
from .interactive_brokers import InteractiveBrokersBroker


class BrokerFactory:
    """브로커 인스턴스 생성 팩토리"""
    
    _brokers: Dict[str, Type[BrokerInterface]] = {
        "alpaca": AlpacaBroker,
        "ib": InteractiveBrokersBroker,
        "interactive_brokers": InteractiveBrokersBroker,
    }
    
    @classmethod
    def create_broker(
        self, 
        broker_name: str, 
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper_trading: bool = True,
        **kwargs
    ) -> BrokerInterface:
        """브로커 인스턴스 생성"""
        broker_name = broker_name.lower()
        
        if broker_name not in self._brokers:
            available = ", ".join(self._brokers.keys())
            raise ValueError(f"지원하지 않는 브로커: {broker_name}. 사용 가능한 브로커: {available}")
        
        broker_class = self._brokers[broker_name]
        
        # 환경변수에서 API 키 가져오기
        if not api_key:
            if broker_name == "alpaca":
                api_key = os.getenv("ALPACA_API_KEY")
                if not secret_key:
                    secret_key = os.getenv("ALPACA_SECRET_KEY")
            elif broker_name in ["ib", "interactive_brokers"]:
                # Interactive Brokers는 API 키가 아닌 TWS/Gateway 연결 사용
                api_key = api_key or ""
                secret_key = secret_key or ""
        
        if broker_name == "alpaca" and (not api_key or not secret_key):
            raise ValueError("Alpaca 브로커는 API_KEY와 SECRET_KEY가 필요합니다")
        
        return broker_class(api_key, secret_key, paper_trading=paper_trading, **kwargs)
    
    @classmethod
    def get_available_brokers(cls) -> List[str]:
        """사용 가능한 브로커 목록 반환"""
        return list(cls._brokers.keys())
    
    @classmethod
    def register_broker(cls, name: str, broker_class: Type[BrokerInterface]):
        """새로운 브로커 등록"""
        cls._brokers[name.lower()] = broker_class