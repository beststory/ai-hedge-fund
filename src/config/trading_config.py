"""거래 설정 관리"""
import os
import json
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BrokerConfig:
    """브로커 설정"""
    name: str = "alpaca"
    paper_trading: bool = True
    api_key: str = ""
    secret_key: str = ""
    host: str = "127.0.0.1"  # Interactive Brokers용
    port: int = 7497  # Interactive Brokers용
    

@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    max_position_size: float = 0.1  # 포트폴리오의 10%
    max_sector_exposure: float = 0.3  # 섹터별 30%
    max_daily_var: float = 0.05  # 일일 VaR 5%
    max_drawdown: float = 0.15  # 최대 드로우다운 15%
    min_liquidity: float = 10000  # 최소 현금 보유
    max_leverage: float = 2.0  # 최대 레버리지 2배
    max_correlation: float = 0.8  # 최대 상관관계
    volatility_threshold: float = 0.25  # 변동성 임계값
    min_confidence: float = 0.7  # 최소 신뢰도


@dataclass
class TradingConfig:
    """거래 설정"""
    dry_run: bool = True  # 시뮬레이션 모드
    auto_trading: bool = False  # 자동 거래 실행
    market_hours_only: bool = True  # 장중에만 거래
    max_daily_trades: int = 50  # 일일 최대 거래 수
    order_timeout: int = 300  # 주문 타임아웃 (초)
    slippage_allowance: float = 0.02  # 슬리피지 허용치 2%
    

@dataclass
class NotificationConfig:
    """알림 설정"""
    email_enabled: bool = False
    email_address: str = ""
    slack_enabled: bool = False
    slack_webhook: str = ""
    critical_alerts_only: bool = False


@dataclass
class AIConfig:
    """AI 에이전트 설정"""
    model_name: str = "gpt-4o"
    model_provider: str = "OpenAI"
    show_reasoning: bool = False
    selected_analysts: list = None
    temperature: float = 0.1
    max_tokens: int = 4000


@dataclass
class AppConfig:
    """전체 애플리케이션 설정"""
    broker: BrokerConfig
    risk: RiskConfig
    trading: TradingConfig
    notifications: NotificationConfig
    ai: AIConfig
    
    def __post_init__(self):
        if self.ai.selected_analysts is None:
            self.ai.selected_analysts = []


class ConfigManager:
    """설정 관리자"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "trading_config.yaml"
        self.env_file = Path(".env")
        
    def load_config(self) -> AppConfig:
        """설정 파일에서 설정 로드"""
        # 기본 설정
        config = AppConfig(
            broker=BrokerConfig(),
            risk=RiskConfig(),
            trading=TradingConfig(),
            notifications=NotificationConfig(),
            ai=AIConfig()
        )
        
        # 환경변수에서 API 키 로드
        self._load_env_variables(config)
        
        # 설정 파일이 있으면 로드
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # 설정 업데이트
                if 'broker' in config_data:
                    for key, value in config_data['broker'].items():
                        if hasattr(config.broker, key):
                            setattr(config.broker, key, value)
                
                if 'risk' in config_data:
                    for key, value in config_data['risk'].items():
                        if hasattr(config.risk, key):
                            setattr(config.risk, key, value)
                
                if 'trading' in config_data:
                    for key, value in config_data['trading'].items():
                        if hasattr(config.trading, key):
                            setattr(config.trading, key, value)
                
                if 'notifications' in config_data:
                    for key, value in config_data['notifications'].items():
                        if hasattr(config.notifications, key):
                            setattr(config.notifications, key, value)
                
                if 'ai' in config_data:
                    for key, value in config_data['ai'].items():
                        if hasattr(config.ai, key):
                            setattr(config.ai, key, value)
            
            except Exception as e:
                print(f"설정 파일 로드 중 오류: {e}")
        
        return config
    
    def save_config(self, config: AppConfig):
        """설정을 파일에 저장"""
        try:
            config_data = {
                'broker': asdict(config.broker),
                'risk': asdict(config.risk),
                'trading': asdict(config.trading),
                'notifications': asdict(config.notifications),
                'ai': asdict(config.ai)
            }
            
            # API 키는 저장하지 않음 (보안)
            config_data['broker']['api_key'] = ""
            config_data['broker']['secret_key'] = ""
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            print(f"설정이 {self.config_file}에 저장되었습니다.")
            
        except Exception as e:
            print(f"설정 저장 중 오류: {e}")
    
    def _load_env_variables(self, config: AppConfig):
        """환경변수에서 API 키 로드"""
        # Alpaca
        if os.getenv("ALPACA_API_KEY"):
            config.broker.api_key = os.getenv("ALPACA_API_KEY", "")
            config.broker.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            if config.ai.model_provider == "OpenAI":
                pass  # 모델에서 자동으로 처리됨
        
        # 알림 설정
        if os.getenv("NOTIFICATION_EMAIL"):
            config.notifications.email_address = os.getenv("NOTIFICATION_EMAIL", "")
            config.notifications.email_enabled = True
        
        if os.getenv("SLACK_WEBHOOK"):
            config.notifications.slack_webhook = os.getenv("SLACK_WEBHOOK", "")
            config.notifications.slack_enabled = True
    
    def create_example_config(self):
        """예제 설정 파일 생성"""
        example_config = AppConfig(
            broker=BrokerConfig(
                name="alpaca",
                paper_trading=True
            ),
            risk=RiskConfig(),
            trading=TradingConfig(),
            notifications=NotificationConfig(),
            ai=AIConfig(
                selected_analysts=[
                    "warren_buffett",
                    "peter_lynch", 
                    "fundamentals",
                    "technicals"
                ]
            )
        )
        
        self.save_config(example_config)
        
        # .env.example 파일도 생성
        env_example = """# 브로커 API 키
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here

# AI 모델 API 키
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# 금융 데이터 API 키
FINANCIAL_DATASETS_API_KEY=your_financial_datasets_api_key_here

# 알림 설정
NOTIFICATION_EMAIL=your_email@example.com
SLACK_WEBHOOK=your_slack_webhook_url_here
"""
        
        env_example_file = Path(".env.example")
        with open(env_example_file, 'w') as f:
            f.write(env_example)
        
        print(f"예제 설정 파일들이 생성되었습니다:")
        print(f"- {self.config_file}")
        print(f"- {env_example_file}")
    
    def validate_config(self, config: AppConfig) -> Dict[str, Any]:
        """설정 검증"""
        errors = []
        warnings = []
        
        # 브로커 설정 검증
        if not config.broker.name:
            errors.append("브로커 이름이 설정되지 않았습니다")
        
        if config.broker.name == "alpaca" and (not config.broker.api_key or not config.broker.secret_key):
            errors.append("Alpaca API 키가 설정되지 않았습니다")
        
        # 리스크 설정 검증
        if config.risk.max_position_size <= 0 or config.risk.max_position_size > 1:
            errors.append("최대 포지션 크기는 0과 1 사이여야 합니다")
        
        if config.risk.min_confidence <= 0 or config.risk.min_confidence > 1:
            errors.append("최소 신뢰도는 0과 1 사이여야 합니다")
        
        # AI 설정 검증
        if not config.ai.model_name:
            errors.append("AI 모델이 설정되지 않았습니다")
        
        # 거래 설정 경고
        if not config.trading.dry_run:
            warnings.append("실제 거래 모드가 활성화되어 있습니다. 주의하세요!")
        
        if config.trading.auto_trading and not config.trading.dry_run:
            warnings.append("자동 거래가 실제 거래 모드에서 활성화되어 있습니다!")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# 글로벌 설정 인스턴스
_config_manager = ConfigManager()
_app_config = None

def get_config() -> AppConfig:
    """전역 설정 인스턴스 반환"""
    global _app_config
    if _app_config is None:
        _app_config = _config_manager.load_config()
    return _app_config

def reload_config() -> AppConfig:
    """설정 재로드"""
    global _app_config
    _app_config = _config_manager.load_config()
    return _app_config

def save_config(config: AppConfig):
    """설정 저장"""
    global _app_config
    _config_manager.save_config(config)
    _app_config = config