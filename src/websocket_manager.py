"""웹소켓 실시간 모니터링"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import weakref


logger = logging.getLogger(__name__)


class ConnectionManager:
    """웹소켓 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now(),
            "subscriptions": set()
        }
        logger.info(f"클라이언트 {client_id} 연결됨")
    
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            client_id = self.connection_data[websocket].get("client_id", "unknown")
            self.active_connections.remove(websocket)
            del self.connection_data[websocket]
            logger.info(f"클라이언트 {client_id} 연결 해제됨")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """개별 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict, subscription_type: str = None):
        """모든 클라이언트에게 브로드캐스트"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                # 구독 타입 확인
                if subscription_type:
                    subscriptions = self.connection_data[connection].get("subscriptions", set())
                    if subscription_type not in subscriptions:
                        continue
                
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"브로드캐스트 실패: {e}")
                disconnected.append(connection)
        
        # 연결이 끊긴 클라이언트 정리
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, subscription_type: str):
        """구독 추가"""
        if websocket in self.connection_data:
            self.connection_data[websocket]["subscriptions"].add(subscription_type)
    
    def unsubscribe(self, websocket: WebSocket, subscription_type: str):
        """구독 해제"""
        if websocket in self.connection_data:
            self.connection_data[websocket]["subscriptions"].discard(subscription_type)
    
    def get_stats(self):
        """연결 통계"""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "client_id": data["client_id"],
                    "connected_at": data["connected_at"].isoformat(),
                    "subscriptions": list(data["subscriptions"])
                }
                for data in self.connection_data.values()
            ]
        }


# 전역 연결 관리자
manager = ConnectionManager()


class RealTimeMonitor:
    """실시간 모니터링 서비스"""
    
    def __init__(self, app_state: Dict):
        self.app_state = weakref.ref(app_state) if isinstance(app_state, dict) else lambda: app_state
        self.monitoring_active = False
        self.monitor_task = None
        
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("실시간 모니터링 시작됨")
    
    async def stop_monitoring(self):
        """모니터링 중단"""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("실시간 모니터링 중단됨")
    
    async def _monitor_loop(self):
        """모니터링 루프"""
        try:
            while self.monitoring_active:
                try:
                    # 시스템 상태 모니터링
                    await self._check_system_status()
                    
                    # 계좌 상태 모니터링
                    await self._check_account_status()
                    
                    # 리스크 모니터링
                    await self._check_risk_status()
                    
                    # 거래 모니터링
                    await self._check_trading_status()
                    
                    # 10초마다 체크
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"모니터링 루프 오류: {e}")
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            logger.info("모니터링 루프가 취소되었습니다")
    
    async def _check_system_status(self):
        """시스템 상태 체크"""
        try:
            app_state = self.app_state()
            if not app_state:
                return
            
            status_data = {
                "type": "system_status",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "system_status": app_state.get("system_status", "unknown"),
                    "broker_connected": app_state.get("broker") is not None,
                    "trading_engine_active": app_state.get("trading_engine") is not None,
                    "risk_monitor_active": app_state.get("risk_monitor") is not None
                }
            }
            
            await manager.broadcast(status_data, "system_status")
            
        except Exception as e:
            logger.error(f"시스템 상태 체크 오류: {e}")
    
    async def _check_account_status(self):
        """계좌 상태 체크"""
        try:
            app_state = self.app_state()
            trading_engine = app_state.get("trading_engine") if app_state else None
            
            if not trading_engine:
                return
            
            account_info = trading_engine.get_account_summary()
            
            account_data = {
                "type": "account_update",
                "timestamp": datetime.now().isoformat(),
                "data": account_info
            }
            
            await manager.broadcast(account_data, "account_status")
            
        except Exception as e:
            logger.error(f"계좌 상태 체크 오류: {e}")
    
    async def _check_risk_status(self):
        """리스크 상태 체크"""
        try:
            app_state = self.app_state()
            risk_monitor = app_state.get("risk_monitor") if app_state else None
            
            if not risk_monitor:
                return
            
            risk_info = risk_monitor.run_risk_check()
            
            risk_data = {
                "type": "risk_update",
                "timestamp": datetime.now().isoformat(),
                "data": risk_info
            }
            
            await manager.broadcast(risk_data, "risk_status")
            
            # 중요한 리스크 알림은 모든 클라이언트에게
            critical_alerts = [alert for alert in risk_info.get("alerts", []) 
                             if alert.get("level") in ["critical", "emergency"]]
            
            if critical_alerts:
                alert_data = {
                    "type": "critical_alert",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "level": "critical",
                        "alerts": critical_alerts
                    }
                }
                await manager.broadcast(alert_data)
            
        except Exception as e:
            logger.error(f"리스크 상태 체크 오류: {e}")
    
    async def _check_trading_status(self):
        """거래 상태 체크"""
        try:
            app_state = self.app_state()
            if not app_state:
                return
            
            # 최근 거래 기록 확인
            trading_history = app_state.get("trading_history", [])
            if trading_history:
                latest_trade = trading_history[-1]
                
                # 최근 5분 이내의 거래만 브로드캐스트
                trade_time = datetime.fromisoformat(latest_trade["timestamp"])
                time_diff = (datetime.now() - trade_time).total_seconds()
                
                if time_diff < 300:  # 5분
                    trade_data = {
                        "type": "recent_trade",
                        "timestamp": datetime.now().isoformat(),
                        "data": latest_trade
                    }
                    
                    await manager.broadcast(trade_data, "trading_status")
            
        except Exception as e:
            logger.error(f"거래 상태 체크 오류: {e}")
    
    async def send_custom_update(self, update_type: str, data: Dict):
        """커스텀 업데이트 전송"""
        message = {
            "type": update_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        await manager.broadcast(message, update_type)


# 전역 모니터 인스턴스 (웹 API에서 초기화)
real_time_monitor = None


async def handle_websocket_message(websocket: WebSocket, data: Dict):
    """웹소켓 메시지 핸들러"""
    message_type = data.get("type")
    
    if message_type == "subscribe":
        subscription_type = data.get("subscription_type")
        if subscription_type:
            manager.subscribe(websocket, subscription_type)
            await manager.send_personal_message({
                "type": "subscription_confirmed",
                "subscription_type": subscription_type
            }, websocket)
    
    elif message_type == "unsubscribe":
        subscription_type = data.get("subscription_type")
        if subscription_type:
            manager.unsubscribe(websocket, subscription_type)
            await manager.send_personal_message({
                "type": "subscription_cancelled",
                "subscription_type": subscription_type
            }, websocket)
    
    elif message_type == "get_stats":
        stats = manager.get_stats()
        await manager.send_personal_message({
            "type": "connection_stats",
            "data": stats
        }, websocket)
    
    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"알 수 없는 메시지 타입: {message_type}"
        }, websocket)