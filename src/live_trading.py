"""실제 거래 시스템 메인"""
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from colorama import Fore, Style, init
import questionary

from src.config.trading_config import ConfigManager, get_config, save_config
from src.brokers.factory import BrokerFactory
from src.execution.trading_engine import TradingEngine, RiskLimits
from src.risk_management.risk_monitor import RiskMonitor
from src.main import run_hedge_fund
from src.utils.display import print_trading_output

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)

init(autoreset=True)


class LiveTradingSystem:
    """실제 거래 시스템"""
    
    def __init__(self):
        self.config = get_config()
        self.broker = None
        self.trading_engine = None
        self.risk_monitor = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            # 설정 검증
            validation = ConfigManager().validate_config(self.config)
            if not validation["valid"]:
                print(f"{Fore.RED}설정 오류:{Style.RESET_ALL}")
                for error in validation["errors"]:
                    print(f"  - {error}")
                return False
            
            if validation["warnings"]:
                print(f"{Fore.YELLOW}경고:{Style.RESET_ALL}")
                for warning in validation["warnings"]:
                    print(f"  - {warning}")
            
            # 브로커 연결
            print(f"{Fore.CYAN}브로커 연결 중...{Style.RESET_ALL}")
            self.broker = BrokerFactory.create_broker(
                broker_name=self.config.broker.name,
                api_key=self.config.broker.api_key,
                secret_key=self.config.broker.secret_key,
                paper_trading=self.config.broker.paper_trading,
                host=self.config.broker.host,
                port=self.config.broker.port
            )
            
            if not self.broker.authenticate():
                print(f"{Fore.RED}브로커 인증 실패{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.GREEN}브로커 연결 성공{Style.RESET_ALL}")
            
            # 리스크 한도 설정
            risk_limits = RiskLimits(
                max_position_size=self.config.risk.max_position_size * 100000,  # 임시로 $100k 기준
                max_total_exposure=self.config.risk.max_sector_exposure * 500000,
                max_daily_loss=self.config.risk.max_drawdown * 100000,
                min_confidence=self.config.risk.min_confidence
            )
            
            # 거래 엔진 초기화
            self.trading_engine = TradingEngine(
                broker=self.broker,
                risk_limits=risk_limits,
                dry_run=self.config.trading.dry_run
            )
            
            # 리스크 모니터 초기화
            self.risk_monitor = RiskMonitor(self.broker)
            
            print(f"{Fore.GREEN}시스템 초기화 완료{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}초기화 실패: {str(e)}{Style.RESET_ALL}")
            self.logger.error(f"시스템 초기화 실패: {str(e)}")
            return False
    
    def run_single_analysis(self, tickers: List[str]) -> Dict[str, Any]:
        """단일 분석 실행"""
        print(f"\n{Fore.CYAN}AI 분석 시작...{Style.RESET_ALL}")
        
        # 날짜 설정
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # 포트폴리오 초기화
        portfolio = {
            "cash": 100000.0,
            "margin_requirement": 0.0,
            "margin_used": 0.0,
            "positions": {ticker: {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0, "short_margin_used": 0.0} for ticker in tickers},
            "realized_gains": {ticker: {"long": 0.0, "short": 0.0} for ticker in tickers}
        }
        
        try:
            # AI 분석 실행
            result = run_hedge_fund(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                portfolio=portfolio,
                show_reasoning=self.config.ai.show_reasoning,
                selected_analysts=self.config.ai.selected_analysts or [],
                model_name=self.config.ai.model_name,
                model_provider=self.config.ai.model_provider
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI 분석 실패: {str(e)}")
            return {"error": str(e)}
    
    def execute_trades(self, ai_decisions: Dict[str, Any]) -> Dict[str, Any]:
        """거래 실행"""
        if "decisions" not in ai_decisions:
            return {"error": "AI 결정 데이터가 없습니다"}
        
        print(f"\n{Fore.CYAN}거래 실행 중...{Style.RESET_ALL}")
        
        # 리스크 체크
        risk_check = self.risk_monitor.run_risk_check()
        if risk_check["status"] == "EMERGENCY":
            print(f"{Fore.RED}긴급 상황 감지 - 거래 중단{Style.RESET_ALL}")
            return {"error": "긴급 상황으로 인한 거래 중단", "risk_status": risk_check}
        
        # 거래 실행
        execution_results = self.trading_engine.execute_signals(ai_decisions["decisions"])
        
        # 결과 출력
        self._print_execution_results(execution_results)
        
        return {
            "execution_results": execution_results,
            "risk_status": risk_check
        }
    
    def _print_execution_results(self, results: Dict[str, Any]):
        """거래 실행 결과 출력"""
        print(f"\n{Fore.YELLOW}=== 거래 실행 결과 ==={Style.RESET_ALL}")
        
        executed_count = 0
        failed_count = 0
        
        for symbol, result in results.items():
            if isinstance(result, dict):
                if result.get("executed", False):
                    status = f"{Fore.GREEN}✅ 성공{Style.RESET_ALL}"
                    executed_count += 1
                else:
                    status = f"{Fore.RED}❌ 실패{Style.RESET_ALL}"
                    failed_count += 1
                
                print(f"{symbol}: {result.get('action', 'N/A')} {result.get('quantity', 0)}주 - {status}")
                if result.get("message"):
                    print(f"  메시지: {result['message']}")
                if result.get("order_id"):
                    print(f"  주문 ID: {result['order_id']}")
        
        print(f"\n실행: {executed_count}건, 실패: {failed_count}건")
    
    def run_continuous_trading(self, tickers: List[str], interval_minutes: int = 60):
        """연속 거래 모드"""
        print(f"{Fore.CYAN}연속 거래 모드 시작 (간격: {interval_minutes}분){Style.RESET_ALL}")
        
        if not self.config.trading.auto_trading:
            print(f"{Fore.YELLOW}자동 거래가 비활성화되어 있어 분석만 실행됩니다{Style.RESET_ALL}")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n{Fore.MAGENTA}=== 반복 {iteration} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ==={Style.RESET_ALL}")
                
                # 시장 개장 여부 확인
                if self.config.trading.market_hours_only and not self.broker.is_market_open():
                    print("시장이 닫혀있어 다음 체크까지 대기합니다")
                    time.sleep(interval_minutes * 60)
                    continue
                
                # AI 분석 실행
                ai_result = self.run_single_analysis(tickers)
                
                if "error" not in ai_result:
                    print_trading_output(ai_result)
                    
                    # 자동 거래가 활성화된 경우에만 실행
                    if self.config.trading.auto_trading:
                        trade_result = self.execute_trades(ai_result)
                        
                        # 리스크 알림 체크
                        if "risk_status" in trade_result:
                            self._handle_risk_alerts(trade_result["risk_status"])
                else:
                    print(f"{Fore.RED}AI 분석 실패: {ai_result['error']}{Style.RESET_ALL}")
                
                # 계좌 상태 출력
                self._print_account_status()
                
                # 대기
                print(f"다음 실행까지 {interval_minutes}분 대기...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}사용자에 의해 중단되었습니다{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}오류 발생: {str(e)}{Style.RESET_ALL}")
            self.logger.error(f"연속 거래 중 오류: {str(e)}")
    
    def _handle_risk_alerts(self, risk_status: Dict[str, Any]):
        """리스크 알림 처리"""
        alerts = risk_status.get("alerts", [])
        critical_alerts = [a for a in alerts if a.get("level") == "critical"]
        emergency_alerts = [a for a in alerts if a.get("level") == "emergency"]
        
        if emergency_alerts:
            print(f"\n{Fore.RED}🚨 긴급 리스크 알림{Style.RESET_ALL}")
            for alert in emergency_alerts:
                print(f"  - {alert['message']}")
            
            # 긴급 정지 여부 확인
            if questionary.confirm("긴급 정지를 실행하시겠습니까?").ask():
                self.emergency_stop()
        
        elif critical_alerts:
            print(f"\n{Fore.YELLOW}⚠️ 심각한 리스크 알림{Style.RESET_ALL}")
            for alert in critical_alerts:
                print(f"  - {alert['message']}")
    
    def _print_account_status(self):
        """계좌 상태 출력"""
        try:
            account_summary = self.trading_engine.get_account_summary()
            
            print(f"\n{Fore.CYAN}=== 계좌 상태 ==={Style.RESET_ALL}")
            print(f"총 자산: ${account_summary.get('total_value', 0):,.2f}")
            print(f"현금: ${account_summary.get('cash', 0):,.2f}")
            print(f"주식: ${account_summary.get('equity', 0):,.2f}")
            print(f"매수력: ${account_summary.get('buying_power', 0):,.2f}")
            
            positions = account_summary.get('positions', [])
            if positions:
                print(f"포지션 ({len(positions)}개):")
                for pos in positions:
                    pnl_color = Fore.GREEN if pos['unrealized_pnl'] >= 0 else Fore.RED
                    print(f"  {pos['symbol']}: {pos['quantity']}주 "
                          f"(${pos['market_value']:,.2f}, "
                          f"{pnl_color}{pos['unrealized_pnl']:+.2f}{Style.RESET_ALL})")
        
        except Exception as e:
            print(f"계좌 상태 조회 실패: {str(e)}")
    
    def emergency_stop(self):
        """긴급 정지"""
        print(f"\n{Fore.RED}🚨 긴급 정지 실행 중...{Style.RESET_ALL}")
        result = self.risk_monitor.emergency_stop()
        
        if result["status"] == "initiated":
            print(f"{Fore.GREEN}긴급 정지 완료{Style.RESET_ALL}")
            print(f"청산 주문: {len(result['orders'])}건")
            
            if result["errors"]:
                print(f"{Fore.YELLOW}오류 발생:{Style.RESET_ALL}")
                for error in result["errors"]:
                    print(f"  {error['symbol']}: {error['error']}")
        else:
            print(f"{Fore.RED}긴급 정지 실패: {result.get('error', '알 수 없는 오류')}{Style.RESET_ALL}")
    
    def interactive_menu(self):
        """대화형 메뉴"""
        while True:
            choice = questionary.select(
                "원하는 작업을 선택하세요:",
                choices=[
                    "단일 분석 실행",
                    "연속 거래 모드",
                    "계좌 상태 확인",
                    "리스크 체크",
                    "설정 관리",
                    "긴급 정지",
                    "종료"
                ]
            ).ask()
            
            if choice == "단일 분석 실행":
                self._menu_single_analysis()
            elif choice == "연속 거래 모드":
                self._menu_continuous_trading()
            elif choice == "계좌 상태 확인":
                self._print_account_status()
            elif choice == "리스크 체크":
                self._menu_risk_check()
            elif choice == "설정 관리":
                self._menu_config_management()
            elif choice == "긴급 정지":
                if questionary.confirm("정말로 긴급 정지를 실행하시겠습니까?").ask():
                    self.emergency_stop()
            elif choice == "종료":
                break
    
    def _menu_single_analysis(self):
        """단일 분석 메뉴"""
        tickers_input = questionary.text(
            "분석할 티커를 입력하세요 (쉼표로 구분):",
            default="AAPL,GOOGL,MSFT,NVDA"
        ).ask()
        
        if tickers_input:
            tickers = [t.strip().upper() for t in tickers_input.split(",")]
            ai_result = self.run_single_analysis(tickers)
            
            if "error" not in ai_result:
                print_trading_output(ai_result)
                
                if questionary.confirm("거래를 실행하시겠습니까?").ask():
                    self.execute_trades(ai_result)
            else:
                print(f"{Fore.RED}분석 실패: {ai_result['error']}{Style.RESET_ALL}")
    
    def _menu_continuous_trading(self):
        """연속 거래 메뉴"""
        tickers_input = questionary.text(
            "거래할 티커를 입력하세요 (쉼표로 구분):",
            default="AAPL,GOOGL,MSFT,NVDA"
        ).ask()
        
        interval = questionary.text(
            "실행 간격(분)을 입력하세요:",
            default="60"
        ).ask()
        
        if tickers_input and interval:
            try:
                tickers = [t.strip().upper() for t in tickers_input.split(",")]
                interval_minutes = int(interval)
                self.run_continuous_trading(tickers, interval_minutes)
            except ValueError:
                print(f"{Fore.RED}잘못된 간격 값입니다{Style.RESET_ALL}")
    
    def _menu_risk_check(self):
        """리스크 체크 메뉴"""
        risk_result = self.risk_monitor.run_risk_check()
        
        print(f"\n{Fore.CYAN}=== 리스크 체크 결과 ==={Style.RESET_ALL}")
        print(f"상태: {risk_result['status']}")
        
        if risk_result.get('alerts'):
            print(f"\n알림 ({len(risk_result['alerts'])}건):")
            for alert in risk_result['alerts']:
                level_color = {
                    'warning': Fore.YELLOW,
                    'critical': Fore.RED,
                    'emergency': Fore.MAGENTA
                }.get(alert['level'], Fore.WHITE)
                
                print(f"  {level_color}{alert['level'].upper()}{Style.RESET_ALL}: {alert['message']}")
        
        if risk_result.get('recommendations'):
            print(f"\n권장사항:")
            for rec in risk_result['recommendations']:
                print(f"  - {rec}")
    
    def _menu_config_management(self):
        """설정 관리 메뉴"""
        config_choice = questionary.select(
            "설정 관리 작업:",
            choices=[
                "현재 설정 보기",
                "설정 수정",
                "설정 저장",
                "설정 다시 로드"
            ]
        ).ask()
        
        if config_choice == "현재 설정 보기":
            print("\n현재 설정:")
            print(f"브로커: {self.config.broker.name} (페이퍼: {self.config.broker.paper_trading})")
            print(f"드라이런: {self.config.trading.dry_run}")
            print(f"자동거래: {self.config.trading.auto_trading}")
            print(f"AI 모델: {self.config.ai.model_name}")
            
        elif config_choice == "설정 저장":
            save_config(self.config)


def main():
    parser = argparse.ArgumentParser(description="AI 헤지펀드 실제 거래 시스템")
    parser.add_argument("--setup", action="store_true", help="초기 설정 생성")
    parser.add_argument("--tickers", type=str, help="거래할 티커 (쉼표로 구분)")
    parser.add_argument("--mode", choices=["single", "continuous", "interactive"], 
                       default="interactive", help="실행 모드")
    parser.add_argument("--interval", type=int, default=60, help="연속 모드 실행 간격(분)")
    
    args = parser.parse_args()
    
    if args.setup:
        # 초기 설정 생성
        config_manager = ConfigManager()
        config_manager.create_example_config()
        print("설정 파일이 생성되었습니다. .env 파일을 편집하여 API 키를 설정하세요.")
        return
    
    # 거래 시스템 초기화
    system = LiveTradingSystem()
    
    if not system.initialize():
        print("시스템 초기화에 실패했습니다.")
        return
    
    # 티커 설정
    tickers = []
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    # 모드별 실행
    if args.mode == "single" and tickers:
        # 단일 분석 모드
        ai_result = system.run_single_analysis(tickers)
        if "error" not in ai_result:
            print_trading_output(ai_result)
            system.execute_trades(ai_result)
        else:
            print(f"분석 실패: {ai_result['error']}")
            
    elif args.mode == "continuous" and tickers:
        # 연속 거래 모드
        system.run_continuous_trading(tickers, args.interval)
        
    else:
        # 대화형 모드
        system.interactive_menu()


if __name__ == "__main__":
    main()