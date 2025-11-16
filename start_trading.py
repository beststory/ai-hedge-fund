#!/usr/bin/env python3
"""
AI 헤지펀드 실제 거래 시스템 시작 스크립트
간단하게 시스템을 시작할 수 있는 스크립트입니다.
"""

import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from colorama import Fore, Style, init
import questionary

init(autoreset=True)

def check_setup():
    """초기 설정 확인"""
    issues = []
    
    # .env 파일 체크
    if not Path('.env').exists():
        issues.append("❌ .env 파일이 없습니다. 먼저 .env.example을 복사하여 .env를 만드세요.")
    
    # API 키 체크 (기본적인 것들만)
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('GROQ_API_KEY'):
        issues.append("⚠️  AI 모델 API 키가 설정되지 않았습니다 (OPENAI_API_KEY 또는 GROQ_API_KEY)")
    
    # 설정 파일 체크
    if not Path('config/trading_config.yaml').exists():
        issues.append("⚠️  설정 파일이 없습니다. 자동으로 생성됩니다.")
    
    return issues

def print_banner():
    """시작 배너 출력"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                AI 헤지펀드 실제 거래 시스템               ║
║                    Live Trading System                   ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}⚠️  경고: 이 시스템을 실제 거래에 사용하기 전에{Style.RESET_ALL}
{Fore.YELLOW}   반드시 페이퍼 트레이딩으로 충분히 테스트하세요!{Style.RESET_ALL}
"""
    print(banner)

def main():
    print_banner()
    
    # 설정 체크
    print(f"{Fore.CYAN}시스템 설정을 확인하는 중...{Style.RESET_ALL}")
    issues = check_setup()
    
    if issues:
        print(f"\n{Fore.YELLOW}다음 문제들이 발견되었습니다:{Style.RESET_ALL}")
        for issue in issues:
            print(f"  {issue}")
        print()
        
        # 자동 설정 제안
        if not Path('config/trading_config.yaml').exists():
            if questionary.confirm("자동으로 기본 설정을 생성하시겠습니까?").ask():
                print(f"{Fore.CYAN}기본 설정을 생성하는 중...{Style.RESET_ALL}")
                try:
                    from src.live_trading import main as live_trading_main
                    sys.argv = ['start_trading.py', '--setup']
                    live_trading_main()
                    print(f"{Fore.GREEN}설정이 생성되었습니다!{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}설정 생성 실패: {str(e)}{Style.RESET_ALL}")
                    return
        
        # .env 파일 가이드
        if not Path('.env').exists():
            print(f"\n{Fore.CYAN}API 키 설정 가이드:{Style.RESET_ALL}")
            print("1. .env.example을 .env로 복사")
            print("2. .env 파일을 열어서 다음 키들을 설정:")
            print("   - ALPACA_API_KEY (Alpaca 거래용)")
            print("   - ALPACA_SECRET_KEY")
            print("   - OPENAI_API_KEY (AI 분석용)")
            print("\n자세한 설정 방법은 LIVE_TRADING_GUIDE.md를 참조하세요.")
            
            if not questionary.confirm("설정을 완료하고 계속 진행하시겠습니까?").ask():
                return
    
    # 모드 선택
    mode = questionary.select(
        "어떤 모드로 시작하시겠습니까?",
        choices=[
            questionary.Choice("🔧 대화형 모드 (메뉴 선택)", "interactive"),
            questionary.Choice("📊 단일 분석 모드 (한 번만 실행)", "single"), 
            questionary.Choice("🔄 연속 거래 모드 (자동 반복)", "continuous"),
            questionary.Choice("⚙️  설정만 생성하고 종료", "setup_only"),
            questionary.Choice("❌ 종료", "exit")
        ]
    ).ask()
    
    if mode == "exit":
        print("시스템을 종료합니다.")
        return
    
    if mode == "setup_only":
        print(f"{Fore.CYAN}설정 파일을 생성합니다...{Style.RESET_ALL}")
        try:
            from src.live_trading import main as live_trading_main
            sys.argv = ['start_trading.py', '--setup']
            live_trading_main()
            print(f"{Fore.GREEN}설정 생성 완료!{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}설정 생성 실패: {str(e)}{Style.RESET_ALL}")
        return
    
    # 티커 입력 (단일/연속 모드의 경우)
    tickers = None
    if mode in ["single", "continuous"]:
        tickers_input = questionary.text(
            "분석할 티커를 입력하세요 (쉼표로 구분, 예: AAPL,GOOGL,MSFT,NVDA):",
            default="AAPL,GOOGL,MSFT,NVDA"
        ).ask()
        
        if not tickers_input:
            print("티커가 입력되지 않았습니다.")
            return
    
    # 연속 모드 설정
    interval = 60
    if mode == "continuous":
        interval_input = questionary.text(
            "실행 간격을 분 단위로 입력하세요:",
            default="60"
        ).ask()
        
        try:
            interval = int(interval_input)
        except ValueError:
            print("잘못된 간격 값입니다. 60분으로 설정합니다.")
            interval = 60
    
    # 안전 확인
    if mode == "continuous":
        print(f"\n{Fore.YELLOW}연속 거래 모드 주의사항:{Style.RESET_ALL}")
        print("- 지속적인 모니터링이 필요합니다")
        print("- 시장 변동에 따른 리스크가 있습니다")
        print("- 언제든지 Ctrl+C로 중단할 수 있습니다")
        
        if not questionary.confirm("계속 진행하시겠습니까?").ask():
            return
    
    # 실행
    print(f"\n{Fore.CYAN}AI 헤지펀드 시스템을 시작합니다...{Style.RESET_ALL}")
    print("LIVE_TRADING_GUIDE.md에서 자세한 사용법을 확인할 수 있습니다.\n")
    
    try:
        from src.live_trading import main as live_trading_main
        
        # sys.argv 설정
        sys.argv = ['live_trading.py', '--mode', mode]
        if tickers_input:
            sys.argv.extend(['--tickers', tickers_input])
        if mode == "continuous":
            sys.argv.extend(['--interval', str(interval)])
        
        # 실행
        live_trading_main()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}사용자에 의해 중단되었습니다.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}오류 발생: {str(e)}{Style.RESET_ALL}")
        print("자세한 오류 정보는 trading.log 파일을 확인하세요.")

if __name__ == "__main__":
    main()