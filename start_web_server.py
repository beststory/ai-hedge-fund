#!/usr/bin/env python3
"""
AI 헤지펀드 웹 서버 시작 스크립트
브라우저에서 접속 가능한 웹 인터페이스 서버를 시작합니다.
"""

import os
import sys
import socket
import webbrowser
import threading
import time
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from colorama import Fore, Style, init
import questionary

init(autoreset=True)


def check_port_available(host, port):
    """포트 사용 가능 여부 확인"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host, start_port, max_attempts=10):
    """사용 가능한 포트 찾기"""
    for i in range(max_attempts):
        port = start_port + i
        if check_port_available(host, port):
            return port
    return None


def open_browser(url, delay=3):
    """브라우저 열기 (지연 후)"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
        print(f"{Fore.GREEN}브라우저가 자동으로 열렸습니다: {url}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}브라우저 자동 열기 실패: {str(e)}{Style.RESET_ALL}")
        print(f"수동으로 브라우저에서 {url}에 접속하세요.")


def print_banner():
    """시작 배너 출력"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                AI 헤지펀드 웹 서버                        ║
║                  Web Interface Server                   ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}🌐 브라우저 기반 AI 헤지펀드 거래 시스템{Style.RESET_ALL}
{Fore.YELLOW}⚠️  실제 거래 전 반드시 페이퍼 트레이딩으로 테스트하세요!{Style.RESET_ALL}
"""
    print(banner)


def check_dependencies():
    """의존성 확인"""
    missing_deps = []
    
    try:
        import uvicorn
    except ImportError:
        missing_deps.append("uvicorn")
    
    try:
        import fastapi
    except ImportError:
        missing_deps.append("fastapi")
    
    if missing_deps:
        print(f"{Fore.RED}❌ 필수 패키지가 설치되지 않았습니다:{Style.RESET_ALL}")
        for dep in missing_deps:
            print(f"   - {dep}")
        print(f"\n{Fore.CYAN}설치 방법:{Style.RESET_ALL}")
        print("poetry install  # 또는")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True


def check_setup():
    """초기 설정 확인"""
    issues = []
    suggestions = []
    
    # .env 파일 체크
    if not Path('.env').exists():
        issues.append("❌ .env 파일이 없습니다")
        suggestions.append("💡 .env.example을 복사하여 .env를 만들고 API 키를 설정하세요")
    
    # API 키 체크 (기본적인 것들만)
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('GROQ_API_KEY'):
        issues.append("⚠️  AI 모델 API 키가 설정되지 않았습니다")
        suggestions.append("💡 .env 파일에 OPENAI_API_KEY 또는 GROQ_API_KEY를 설정하세요")
    
    # 웹 디렉토리 체크
    if not Path('web/index.html').exists():
        issues.append("❌ 웹 인터페이스 파일이 없습니다")
        suggestions.append("💡 web/index.html 파일이 필요합니다")
    
    return issues, suggestions


def get_server_config():
    """서버 설정 가져오기"""
    config = {
        "host": "0.0.0.0",
        "port": 8888,
        "auto_open": True,
        "dev_mode": False
    }
    
    # 환경변수에서 설정 오버라이드
    if os.getenv('WEB_HOST'):
        config["host"] = os.getenv('WEB_HOST')
    
    if os.getenv('WEB_PORT'):
        try:
            config["port"] = int(os.getenv('WEB_PORT'))
        except ValueError:
            pass
    
    return config


def main():
    print_banner()
    
    # 의존성 확인
    if not check_dependencies():
        return 1
    
    # 설정 확인
    print(f"{Fore.CYAN}시스템 설정을 확인하는 중...{Style.RESET_ALL}")
    issues, suggestions = check_setup()
    
    if issues:
        print(f"\n{Fore.YELLOW}발견된 문제들:{Style.RESET_ALL}")
        for issue in issues:
            print(f"  {issue}")
        
        if suggestions:
            print(f"\n{Fore.CYAN}해결 방법:{Style.RESET_ALL}")
            for suggestion in suggestions:
                print(f"  {suggestion}")
        
        print()
        if not questionary.confirm("문제가 있지만 계속 진행하시겠습니까?").ask():
            return 1
    
    # 서버 설정
    config = get_server_config()
    
    # 고급 설정 옵션
    if questionary.confirm("고급 설정을 하시겠습니까?").ask():
        config["host"] = questionary.text(
            "호스트 주소:",
            default=config["host"]
        ).ask()
        
        port_input = questionary.text(
            "포트 번호:",
            default=str(config["port"])
        ).ask()
        
        try:
            config["port"] = int(port_input)
        except ValueError:
            print(f"{Fore.YELLOW}잘못된 포트 번호, 기본값 사용: {config['port']}{Style.RESET_ALL}")
        
        config["auto_open"] = questionary.confirm("브라우저 자동 열기:").ask()
        config["dev_mode"] = questionary.confirm("개발자 모드 (자동 재시작):").ask()
    
    # 포트 사용 가능 확인
    if not check_port_available(config["host"], config["port"]):
        print(f"{Fore.YELLOW}포트 {config['port']}가 이미 사용 중입니다. 다른 포트를 찾는 중...{Style.RESET_ALL}")
        
        new_port = find_available_port(config["host"], config["port"] + 1)
        if new_port:
            config["port"] = new_port
            print(f"{Fore.GREEN}포트 {new_port}를 사용합니다.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}사용 가능한 포트를 찾을 수 없습니다.{Style.RESET_ALL}")
            return 1
    
    # 서버 정보 출력
    local_url = f"http://localhost:{config['port']}"
    network_url = f"http://192.168.1.3:{config['port']}"  # 사용자가 제공한 서버 IP
    
    print(f"\n{Fore.CYAN}🚀 AI 헤지펀드 웹 서버 시작 중...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📍 접속 주소:{Style.RESET_ALL}")
    print(f"   로컬: {local_url}")
    print(f"   네트워크: {network_url}")
    print(f"\n{Fore.YELLOW}💡 사용법:{Style.RESET_ALL}")
    print("   1. 브라우저에서 위 주소로 접속")
    print("   2. '시스템 초기화' 버튼 클릭")
    print("   3. 티커 입력 후 'AI 분석 실행'")
    print("   4. 분석 결과 확인 후 '거래 실행'")
    print(f"\n{Fore.CYAN}🔧 제어:{Style.RESET_ALL}")
    print("   Ctrl+C : 서버 종료")
    print()
    
    # 브라우저 자동 열기 (별도 스레드에서)
    if config["auto_open"]:
        browser_thread = threading.Thread(target=open_browser, args=(local_url,))
        browser_thread.daemon = True
        browser_thread.start()
    
    # 서버 시작
    try:
        import uvicorn
        
        # 서버 실행
        uvicorn.run(
            "src.web_api:app",
            host=config["host"],
            port=config["port"],
            reload=config["dev_mode"],
            log_level="info" if config["dev_mode"] else "warning",
            access_log=config["dev_mode"]
        )
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}서버가 사용자에 의해 중단되었습니다.{Style.RESET_ALL}")
        return 0
    except Exception as e:
        print(f"\n{Fore.RED}서버 시작 실패: {str(e)}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)