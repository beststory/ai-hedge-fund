"""간단한 웹 인증 시스템"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# PyJWT 토큰 만료 시간 설정을 위한 import
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8시간


# 기본 설정
SECRET_KEY = os.getenv("WEB_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"

# 기본 사용자 (환경변수에서 설정 가능)
DEFAULT_USERNAME = os.getenv("WEB_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("WEB_PASSWORD", "hedge2024!")

# 사용자 데이터베이스 (실제로는 데이터베이스 사용 권장)
users_db = {
    DEFAULT_USERNAME: {
        "username": DEFAULT_USERNAME,
        "password_hash": hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest(),
        "is_active": True,
        "created_at": datetime.now()
    }
}

# 활성 토큰 저장소
active_tokens: Dict[str, Dict] = {}

# JWT 토큰 인증
security = HTTPBearer(auto_error=False)


class AuthManager:
    """인증 관리자"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해시화"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return AuthManager.hash_password(plain_password) == hashed_password
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        """사용자 인증"""
        user = users_db.get(username)
        if not user:
            return None
        if not AuthManager.verify_password(password, user["password_hash"]):
            return None
        if not user.get("is_active", True):
            return None
        return user
    
    @staticmethod
    def create_access_token(data: Dict) -> str:
        """JWT 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # 활성 토큰 저장
        active_tokens[token] = {
            "username": data.get("sub"),
            "created_at": datetime.utcnow(),
            "expires_at": expire
        }
        
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """토큰 검증"""
        try:
            # JWT 디코딩
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            
            if username is None:
                return None
            
            # 활성 토큰 확인
            if token not in active_tokens:
                return None
            
            # 사용자 존재 확인
            user = users_db.get(username)
            if user is None or not user.get("is_active", True):
                return None
            
            return {"username": username, "user": user}
            
        except jwt.ExpiredSignatureError:
            # 만료된 토큰 정리
            if token in active_tokens:
                del active_tokens[token]
            return None
        except jwt.JWTError:
            return None
    
    @staticmethod
    def logout_token(token: str) -> bool:
        """토큰 로그아웃 (무효화)"""
        if token in active_tokens:
            del active_tokens[token]
            return True
        return False
    
    @staticmethod
    def cleanup_expired_tokens():
        """만료된 토큰 정리"""
        now = datetime.utcnow()
        expired_tokens = []
        
        for token, info in active_tokens.items():
            if info["expires_at"] < now:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del active_tokens[token]
        
        return len(expired_tokens)
    
    @staticmethod
    def get_active_sessions() -> Dict:
        """활성 세션 정보"""
        AuthManager.cleanup_expired_tokens()
        return {
            "active_sessions": len(active_tokens),
            "sessions": [
                {
                    "username": info["username"],
                    "created_at": info["created_at"].isoformat(),
                    "expires_at": info["expires_at"].isoformat()
                }
                for info in active_tokens.values()
            ]
        }


# FastAPI 의존성
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """현재 사용자 가져오기"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_info = AuthManager.verify_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


# 선택적 인증 (토큰이 없어도 허용)
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """선택적 사용자 인증"""
    if not credentials:
        return None
    
    token = credentials.credentials
    return AuthManager.verify_token(token)


def init_auth():
    """인증 시스템 초기화"""
    print(f"🔐 웹 인증 시스템 초기화")
    print(f"기본 계정: {DEFAULT_USERNAME}")
    print(f"기본 비밀번호: {DEFAULT_PASSWORD}")
    print(f"⚠️  보안을 위해 환경변수로 계정 정보를 설정하세요:")
    print(f"   WEB_USERNAME=your_username")
    print(f"   WEB_PASSWORD=your_password")
    print(f"   WEB_SECRET_KEY=your_secret_key")


def create_user(username: str, password: str, is_active: bool = True) -> bool:
    """새 사용자 생성"""
    if username in users_db:
        return False
    
    users_db[username] = {
        "username": username,
        "password_hash": AuthManager.hash_password(password),
        "is_active": is_active,
        "created_at": datetime.now()
    }
    
    return True


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """비밀번호 변경"""
    user = users_db.get(username)
    if not user:
        return False
    
    if not AuthManager.verify_password(old_password, user["password_hash"]):
        return False
    
    user["password_hash"] = AuthManager.hash_password(new_password)
    return True


def get_login_info():
    """로그인 정보 반환"""
    return {
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
        "note": "환경변수 WEB_USERNAME, WEB_PASSWORD로 변경 가능"
    }