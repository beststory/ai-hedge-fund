"""실제 거래 엔진"""
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from src.brokers.base import BrokerInterface, OrderSide, OrderType, OrderStatus
from src.brokers.factory import BrokerFactory


@dataclass
class TradeSignal:
    """거래 신호"""
    symbol: str
    action: str  # "buy", "sell", "short", "cover", "hold"
    quantity: int
    confidence: float
    reasoning: str
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None


@dataclass
class RiskLimits:
    """리스크 한도"""
    max_position_size: float = 10000  # 단일 포지션 최대 금액
    max_total_exposure: float = 50000  # 전체 노출 한도
    max_daily_loss: float = 5000  # 일일 최대 손실
    max_portfolio_volatility: float = 0.02  # 최대 포트폴리오 변동성
    min_confidence: float = 0.7  # 최소 신뢰도


class TradingEngine:
    """실제 거래 실행 엔진"""
    
    def __init__(self, broker: BrokerInterface, risk_limits: Optional[RiskLimits] = None, dry_run: bool = True):
        self.broker = broker
        self.risk_limits = risk_limits or RiskLimits()
        self.dry_run = dry_run  # True이면 실제 거래하지 않고 시뮬레이션만
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 오늘의 거래 기록
        self.daily_trades = []
        self.daily_pnl = 0.0
        
    def execute_signals(self, signals: Dict[str, Dict]) -> Dict[str, Any]:
        """AI 신호를 받아 실제 거래 실행"""
        results = {}
        
        # 시장 개장 여부 확인
        if not self.broker.is_market_open() and not self.dry_run:
            return {"error": "시장이 개장하지 않아 거래할 수 없습니다"}
        
        # 계좌 정보 조회
        try:
            account = self.broker.get_account()
        except Exception as e:
            return {"error": f"계좌 정보를 가져올 수 없습니다: {str(e)}"}
        
        for symbol, signal_data in signals.items():
            try:
                # 신호를 TradeSignal 객체로 변환
                signal = TradeSignal(
                    symbol=symbol,
                    action=signal_data.get("action", "hold"),
                    quantity=int(signal_data.get("quantity", 0)),
                    confidence=float(signal_data.get("confidence", 0)),
                    reasoning=signal_data.get("reasoning", ""),
                    price_target=signal_data.get("price_target"),
                    stop_loss=signal_data.get("stop_loss")
                )
                
                # 거래 실행
                result = self._execute_single_signal(signal, account)
                results[symbol] = result
                
            except Exception as e:
                self.logger.error(f"{symbol} 거래 실행 중 오류: {str(e)}")
                results[symbol] = {"error": str(e), "executed": False}
        
        return results
    
    def _execute_single_signal(self, signal: TradeSignal, account) -> Dict[str, Any]:
        """단일 신호 실행"""
        result = {
            "symbol": signal.symbol,
            "action": signal.action,
            "quantity": signal.quantity,
            "confidence": signal.confidence,
            "executed": False,
            "order_id": None,
            "message": ""
        }
        
        # Hold 액션은 실행하지 않음
        if signal.action == "hold" or signal.quantity == 0:
            result["message"] = "보유 유지"
            return result
        
        # 리스크 체크
        risk_check = self._check_risk(signal, account)
        if not risk_check["passed"]:
            result["message"] = f"리스크 체크 실패: {risk_check['reason']}"
            return result
        
        # 현재 가격 조회
        try:
            current_price = self.broker.get_current_price(signal.symbol)
        except Exception as e:
            result["message"] = f"현재 가격 조회 실패: {str(e)}"
            return result
        
        # 주문 실행
        try:
            order_result = self._place_order(signal, current_price)
            result.update(order_result)
            
            if result["executed"]:
                # 거래 기록 저장
                self.daily_trades.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "signal": signal,
                    "result": result
                })
                
        except Exception as e:
            result["message"] = f"주문 실행 실패: {str(e)}"
        
        return result
    
    def _check_risk(self, signal: TradeSignal, account) -> Dict[str, Any]:
        """리스크 체크"""
        # 신뢰도 체크
        if signal.confidence < self.risk_limits.min_confidence:
            return {
                "passed": False,
                "reason": f"신뢰도 부족 ({signal.confidence:.2f} < {self.risk_limits.min_confidence})"
            }
        
        # 현재 포지션 확인
        current_position = None
        for pos in account.positions:
            if pos.symbol == signal.symbol:
                current_position = pos
                break
        
        # 포지션 크기 체크 (대략적인 금액 계산)
        try:
            current_price = self.broker.get_current_price(signal.symbol)
            position_value = abs(signal.quantity) * current_price
            
            if position_value > self.risk_limits.max_position_size:
                return {
                    "passed": False,
                    "reason": f"포지션 크기 초과 (${position_value:.2f} > ${self.risk_limits.max_position_size})"
                }
        except:
            # 가격 조회 실패 시 보수적으로 거부
            return {"passed": False, "reason": "현재 가격 조회 실패"}
        
        # 일일 손실 체크
        if abs(self.daily_pnl) > self.risk_limits.max_daily_loss:
            return {
                "passed": False,
                "reason": f"일일 최대 손실 초과 (${abs(self.daily_pnl):.2f} > ${self.risk_limits.max_daily_loss})"
            }
        
        # 매도/커버 시 포지션 체크
        if signal.action in ["sell", "cover"]:
            if not current_position:
                return {"passed": False, "reason": f"{signal.action} 할 포지션이 없습니다"}
            
            if signal.action == "sell" and current_position.side != "long":
                return {"passed": False, "reason": "롱 포지션이 없어 매도할 수 없습니다"}
            
            if signal.action == "cover" and current_position.side != "short":
                return {"passed": False, "reason": "숏 포지션이 없어 커버할 수 없습니다"}
            
            if abs(signal.quantity) > abs(current_position.quantity):
                return {"passed": False, "reason": "보유 수량보다 많은 수량을 거래할 수 없습니다"}
        
        return {"passed": True, "reason": "리스크 체크 통과"}
    
    def _place_order(self, signal: TradeSignal, current_price: float) -> Dict[str, Any]:
        """실제 주문 실행"""
        result = {"executed": False, "order_id": None, "message": ""}
        
        # 액션에 따른 주문 방향 결정
        if signal.action in ["buy", "cover"]:
            side = OrderSide.BUY
        elif signal.action in ["sell", "short"]:
            side = OrderSide.SELL
        else:
            result["message"] = f"알 수 없는 액션: {signal.action}"
            return result
        
        # 주문 타입 결정 (기본적으로 시장가)
        order_type = OrderType.MARKET
        limit_price = None
        
        # 가격 목표가 있으면 지정가 주문 사용
        if signal.price_target:
            order_type = OrderType.LIMIT
            limit_price = signal.price_target
        
        if self.dry_run:
            # 시뮬레이션 모드
            result["executed"] = True
            result["order_id"] = f"SIM_{int(time.time())}"
            result["message"] = f"시뮬레이션: {side.value} {signal.quantity}주 @ ${current_price:.2f}"
            self.logger.info(f"[DRY RUN] {signal.symbol}: {result['message']}")
            return result
        
        # 실제 주문 실행
        try:
            order = self.broker.place_order(
                symbol=signal.symbol,
                quantity=abs(signal.quantity),
                side=side,
                order_type=order_type,
                limit_price=limit_price
            )
            
            result["executed"] = True
            result["order_id"] = order.order_id
            result["message"] = f"주문 완료: {side.value} {signal.quantity}주"
            
            self.logger.info(f"{signal.symbol}: {result['message']} (주문 ID: {order.order_id})")
            
        except Exception as e:
            result["message"] = f"주문 실패: {str(e)}"
            self.logger.error(f"{signal.symbol} 주문 실패: {str(e)}")
        
        return result
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            order = self.broker.get_order_status(order_id)
            return {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity,
                "remaining_quantity": order.quantity - order.filled_quantity
            }
        except Exception as e:
            return {"error": str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] 주문 취소: {order_id}")
            return True
        
        return self.broker.cancel_order(order_id)
    
    def get_account_summary(self) -> Dict[str, Any]:
        """계좌 요약 정보"""
        try:
            account = self.broker.get_account()
            return {
                "account_id": account.account_id,
                "buying_power": account.buying_power,
                "total_value": account.total_value,
                "cash": account.cash,
                "equity": account.equity,
                "positions_count": len(account.positions),
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "quantity": pos.quantity,
                        "market_value": pos.market_value,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "side": pos.side
                    }
                    for pos in account.positions
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def reset_daily_stats(self):
        """일일 통계 리셋"""
        self.daily_trades = []
        self.daily_pnl = 0.0