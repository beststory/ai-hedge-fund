"""실시간 리스크 모니터링"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from src.brokers.base import BrokerInterface, Position
from src.tools.api import get_price_data


@dataclass
class RiskAlert:
    """리스크 알림"""
    level: str  # "warning", "critical", "emergency"
    message: str
    timestamp: datetime
    affected_positions: List[str]
    suggested_action: str


@dataclass
class PortfolioMetrics:
    """포트폴리오 메트릭"""
    total_value: float
    total_pnl: float
    daily_pnl: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float  # 95% Value at Risk
    beta: float
    correlation_risk: float


class RiskMonitor:
    """실시간 리스크 모니터링 시스템"""
    
    def __init__(self, broker: BrokerInterface):
        self.broker = broker
        self.alerts = []
        self.historical_data = {}
        
        # 리스크 한도 설정
        self.risk_limits = {
            "max_position_size": 0.1,  # 포트폴리오의 10%
            "max_sector_exposure": 0.3,  # 섹터별 30%
            "max_daily_var": 0.05,  # 일일 VaR 5%
            "max_drawdown": 0.15,  # 최대 드로우다운 15%
            "min_liquidity": 10000,  # 최소 현금 보유
            "max_leverage": 2.0,  # 최대 레버리지 2배
            "max_correlation": 0.8,  # 최대 상관관계
            "volatility_threshold": 0.25  # 변동성 임계값
        }
        
        self.logger = logging.getLogger(__name__)
    
    def run_risk_check(self) -> Dict[str, Any]:
        """전체 리스크 체크 실행"""
        results = {
            "status": "OK",
            "alerts": [],
            "metrics": {},
            "recommendations": []
        }
        
        try:
            # 계좌 정보 조회
            account = self.broker.get_account()
            positions = account.positions
            
            # 포트폴리오 메트릭 계산
            metrics = self.calculate_portfolio_metrics(account)
            results["metrics"] = metrics.__dict__
            
            # 각종 리스크 체크 실행
            checks = [
                self._check_position_concentration(positions, account.total_value),
                self._check_liquidity(account),
                self._check_volatility(positions),
                self._check_drawdown(account),
                self._check_correlation_risk(positions),
                self._check_leverage(account),
            ]
            
            # 알림 수집
            all_alerts = []
            for check_alerts in checks:
                all_alerts.extend(check_alerts)
            
            results["alerts"] = [alert.__dict__ for alert in all_alerts]
            
            # 전체 상태 결정
            critical_alerts = [a for a in all_alerts if a.level == "critical"]
            emergency_alerts = [a for a in all_alerts if a.level == "emergency"]
            
            if emergency_alerts:
                results["status"] = "EMERGENCY"
            elif critical_alerts:
                results["status"] = "CRITICAL"
            elif all_alerts:
                results["status"] = "WARNING"
            
            # 권장사항 생성
            results["recommendations"] = self._generate_recommendations(all_alerts, metrics)
            
        except Exception as e:
            results["status"] = "ERROR"
            results["error"] = str(e)
            self.logger.error(f"리스크 체크 실행 중 오류: {str(e)}")
        
        return results
    
    def calculate_portfolio_metrics(self, account) -> PortfolioMetrics:
        """포트폴리오 메트릭 계산"""
        positions = account.positions
        total_value = account.total_value
        
        if not positions or total_value <= 0:
            return PortfolioMetrics(
                total_value=total_value,
                total_pnl=0,
                daily_pnl=0,
                volatility=0,
                sharpe_ratio=0,
                max_drawdown=0,
                var_95=0,
                beta=0,
                correlation_risk=0
            )
        
        # 수익률 계산
        total_pnl = sum(pos.unrealized_pnl for pos in positions)
        
        # 일일 수익률 계산을 위한 가격 데이터 수집
        try:
            returns = self._calculate_portfolio_returns(positions)
            daily_pnl = returns[-1] * total_value if len(returns) > 0 else 0
            volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
            
            # 샤프 비율 (무위험 수익률을 0으로 가정)
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            # 최대 드로우다운
            cumulative_returns = np.cumprod(1 + np.array(returns))
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
            
            # VaR 계산 (95% 신뢰수준)
            var_95 = np.percentile(returns, 5) * total_value if len(returns) > 0 else 0
            
            # 베타 계산 (SPY 대비, 간단히 1.0으로 설정)
            beta = 1.0
            
            # 상관관계 리스크 (포지션간 평균 상관관계)
            correlation_risk = self._calculate_correlation_risk(positions)
            
        except Exception as e:
            self.logger.warning(f"메트릭 계산 중 오류: {str(e)}")
            daily_pnl = volatility = sharpe_ratio = max_drawdown = var_95 = beta = correlation_risk = 0
        
        return PortfolioMetrics(
            total_value=total_value,
            total_pnl=total_pnl,
            daily_pnl=daily_pnl,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            beta=beta,
            correlation_risk=correlation_risk
        )
    
    def _calculate_portfolio_returns(self, positions: List[Position]) -> List[float]:
        """포트폴리오 수익률 계산"""
        if not positions:
            return []
        
        # 최근 30일 데이터 수집
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        portfolio_returns = []
        weights = {}
        
        # 포지션 가중치 계산
        total_value = sum(abs(pos.market_value) for pos in positions)
        if total_value == 0:
            return []
        
        for pos in positions:
            weights[pos.symbol] = abs(pos.market_value) / total_value
        
        try:
            # 각 종목별 수익률 데이터 수집
            symbol_returns = {}
            for pos in positions:
                try:
                    price_data = get_price_data(pos.symbol, start_date, end_date)
                    if len(price_data) > 1:
                        returns = price_data['close'].pct_change().dropna()
                        symbol_returns[pos.symbol] = returns.tolist()
                except:
                    continue
            
            if not symbol_returns:
                return []
            
            # 최소 공통 기간 찾기
            min_length = min(len(returns) for returns in symbol_returns.values())
            if min_length == 0:
                return []
            
            # 포트폴리오 수익률 계산
            for i in range(min_length):
                portfolio_return = 0
                for symbol, weight in weights.items():
                    if symbol in symbol_returns and i < len(symbol_returns[symbol]):
                        portfolio_return += weight * symbol_returns[symbol][i]
                portfolio_returns.append(portfolio_return)
            
        except Exception as e:
            self.logger.warning(f"수익률 계산 중 오류: {str(e)}")
        
        return portfolio_returns
    
    def _calculate_correlation_risk(self, positions: List[Position]) -> float:
        """포지션간 상관관계 위험 계산"""
        if len(positions) < 2:
            return 0.0
        
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            
            price_data = {}
            for pos in positions:
                try:
                    data = get_price_data(pos.symbol, start_date, end_date)
                    if len(data) > 10:  # 최소 10일 데이터
                        price_data[pos.symbol] = data['close'].pct_change().dropna()
                except:
                    continue
            
            if len(price_data) < 2:
                return 0.0
            
            # 상관관계 매트릭스 계산
            df = pd.DataFrame(price_data)
            correlation_matrix = df.corr()
            
            # 평균 절대 상관관계 계산
            correlations = []
            for i in range(len(correlation_matrix)):
                for j in range(i + 1, len(correlation_matrix)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if not np.isnan(corr_value):
                        correlations.append(abs(corr_value))
            
            return np.mean(correlations) if correlations else 0.0
            
        except Exception as e:
            self.logger.warning(f"상관관계 계산 중 오류: {str(e)}")
            return 0.0
    
    def _check_position_concentration(self, positions: List[Position], total_value: float) -> List[RiskAlert]:
        """포지션 집중도 체크"""
        alerts = []
        
        if total_value <= 0:
            return alerts
        
        for pos in positions:
            position_weight = abs(pos.market_value) / total_value
            
            if position_weight > self.risk_limits["max_position_size"]:
                alerts.append(RiskAlert(
                    level="critical" if position_weight > 0.2 else "warning",
                    message=f"{pos.symbol} 포지션이 과도하게 집중됨 ({position_weight:.1%})",
                    timestamp=datetime.now(),
                    affected_positions=[pos.symbol],
                    suggested_action="포지션 크기 축소 검토"
                ))
        
        return alerts
    
    def _check_liquidity(self, account) -> List[RiskAlert]:
        """유동성 체크"""
        alerts = []
        
        if account.cash < self.risk_limits["min_liquidity"]:
            alerts.append(RiskAlert(
                level="critical" if account.cash < 5000 else "warning",
                message=f"현금 보유량이 부족함 (${account.cash:,.2f})",
                timestamp=datetime.now(),
                affected_positions=[],
                suggested_action="현금 확보를 위한 일부 포지션 청산 검토"
            ))
        
        return alerts
    
    def _check_volatility(self, positions: List[Position]) -> List[RiskAlert]:
        """변동성 체크"""
        alerts = []
        
        for pos in positions:
            try:
                # 최근 30일 변동성 계산
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                price_data = get_price_data(pos.symbol, start_date, end_date)
                if len(price_data) > 5:
                    returns = price_data['close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252)  # 연환산
                    
                    if volatility > self.risk_limits["volatility_threshold"]:
                        alerts.append(RiskAlert(
                            level="warning",
                            message=f"{pos.symbol}의 변동성이 높음 ({volatility:.1%})",
                            timestamp=datetime.now(),
                            affected_positions=[pos.symbol],
                            suggested_action="포지션 크기 조정 또는 헷지 검토"
                        ))
            except:
                continue
        
        return alerts
    
    def _check_drawdown(self, account) -> List[RiskAlert]:
        """드로우다운 체크"""
        alerts = []
        
        # 간단한 드로우다운 체크 (실제로는 더 정교한 계산 필요)
        unrealized_pnl = sum(pos.unrealized_pnl for pos in account.positions)
        if account.total_value > 0:
            current_drawdown = abs(min(0, unrealized_pnl)) / account.total_value
            
            if current_drawdown > self.risk_limits["max_drawdown"]:
                alerts.append(RiskAlert(
                    level="critical",
                    message=f"포트폴리오 드로우다운이 한계 초과 ({current_drawdown:.1%})",
                    timestamp=datetime.now(),
                    affected_positions=[pos.symbol for pos in account.positions],
                    suggested_action="손실 제한을 위한 포지션 정리 검토"
                ))
        
        return alerts
    
    def _check_correlation_risk(self, positions: List[Position]) -> List[RiskAlert]:
        """상관관계 위험 체크"""
        alerts = []
        
        correlation_risk = self._calculate_correlation_risk(positions)
        if correlation_risk > self.risk_limits["max_correlation"]:
            alerts.append(RiskAlert(
                level="warning",
                message=f"포지션간 상관관계가 높음 ({correlation_risk:.2f})",
                timestamp=datetime.now(),
                affected_positions=[pos.symbol for pos in positions],
                suggested_action="분산투자 강화 또는 상관관계가 낮은 자산 추가"
            ))
        
        return alerts
    
    def _check_leverage(self, account) -> List[RiskAlert]:
        """레버리지 체크"""
        alerts = []
        
        if account.equity > 0:
            leverage = account.total_value / account.equity
            
            if leverage > self.risk_limits["max_leverage"]:
                alerts.append(RiskAlert(
                    level="critical" if leverage > 3.0 else "warning",
                    message=f"레버리지가 과도함 ({leverage:.2f}배)",
                    timestamp=datetime.now(),
                    affected_positions=[],
                    suggested_action="레버리지 축소를 위한 포지션 정리"
                ))
        
        return alerts
    
    def _generate_recommendations(self, alerts: List[RiskAlert], metrics: PortfolioMetrics) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 알림 기반 권장사항
        critical_alerts = [a for a in alerts if a.level == "critical"]
        if critical_alerts:
            recommendations.append("즉시 조치가 필요한 리스크가 감지되었습니다.")
        
        # 메트릭 기반 권장사항
        if metrics.volatility > 0.25:
            recommendations.append("포트폴리오 변동성이 높습니다. 위험 자산 비중을 줄이는 것을 고려하세요.")
        
        if metrics.sharpe_ratio < 0:
            recommendations.append("포트폴리오 성과가 부진합니다. 투자 전략을 재검토하세요.")
        
        if metrics.max_drawdown > 0.1:
            recommendations.append("드로우다운이 큽니다. 손실 제한 전략을 강화하세요.")
        
        if metrics.correlation_risk > 0.7:
            recommendations.append("포지션간 상관관계가 높습니다. 분산투자를 늘리세요.")
        
        return recommendations
    
    def emergency_stop(self) -> Dict[str, Any]:
        """긴급 정지 - 모든 포지션 청산"""
        results = {"status": "initiated", "orders": [], "errors": []}
        
        try:
            account = self.broker.get_account()
            
            for pos in account.positions:
                if pos.quantity != 0:
                    try:
                        # 포지션 방향에 따라 반대 주문 실행
                        if pos.quantity > 0:  # 롱 포지션
                            order = self.broker.place_order(
                                pos.symbol, abs(pos.quantity), "sell", "market"
                            )
                        else:  # 숏 포지션
                            order = self.broker.place_order(
                                pos.symbol, abs(pos.quantity), "buy", "market"
                            )
                        
                        results["orders"].append({
                            "symbol": pos.symbol,
                            "order_id": order.order_id,
                            "quantity": abs(pos.quantity)
                        })
                        
                    except Exception as e:
                        results["errors"].append({
                            "symbol": pos.symbol,
                            "error": str(e)
                        })
            
            self.logger.critical("긴급 정지 실행 완료")
            
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.logger.error(f"긴급 정지 실행 중 오류: {str(e)}")
        
        return results