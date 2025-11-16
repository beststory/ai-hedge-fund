# 단종제품 검색 플랫폼 PRD (Product Requirements Document)

## 📋 프로젝트 개요

### 목적
단종된 제품들을 등록하고 사용자가 검색하여, 판매자와 연락할 수 있는 B2C/C2C 마켓플레이스 플랫폼 구축

### 비전
"필요한 단종제품을 쉽게 찾고, 신뢰할 수 있는 판매자와 안전하게 거래할 수 있는 플랫폼"

### 핵심 가치 제안
- **구매자**: 찾기 어려운 단종제품을 빠르게 검색하고 가격/재고 정보 확인
- **판매자**: 재고 단종제품을 효과적으로 판매할 수 있는 채널 확보
- **플랫폼**: 거래 중개 및 안전한 거래 환경 제공

---

## 🎯 핵심 기능 (MVP)

### 1. 사용자 인증 시스템
**재사용 컴포넌트**: AI 헤지펀드의 JWT 인증 시스템
- 회원가입/로그인 (이메일, 소셜 로그인)
- 사용자 유형: 일반 구매자, 판매자, 관리자
- JWT 토큰 기반 세션 관리
- 비밀번호 암호화 (bcrypt)

**환경변수 (.env)**:
```
WEB_USERNAME=admin
WEB_PASSWORD=secure_password
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### 2. 제품 등록 시스템 (판매자)
**신규 기능**

#### 2.1 제품 정보 입력 폼
- **필수 정보**:
  - 제품명 (브랜드 + 모델명)
  - 카테고리 (전자제품, 가전, 자동차 부품, 산업자재 등)
  - 제조사/브랜드
  - 모델번호
  - 단종 연도/월
  - 제품 상태 (신품, 중고-상급, 중고-중급, 중고-하급, 부품용)
  - 수량
  - 가격 (판매가, 협의가능 여부)

- **선택 정보**:
  - 제품 설명
  - 제품 이미지 (최대 10장)
  - 제품 스펙/기술 문서
  - 원산지
  - 보관 상태
  - 보증/보장 정보

#### 2.2 이미지 업로드
- 다중 이미지 업로드 (드래그 앤 드롭)
- 이미지 압축 및 최적화
- 썸네일 자동 생성
- 클라우드 스토리지 연동 (AWS S3, Cloudflare R2 등)

#### 2.3 판매자 정보
- 상호명/업체명
- 사업자등록번호 (선택)
- 연락처 (전화번호, 이메일)
- 주소 (지역 정보)
- 판매자 인증 배지 시스템

### 3. 제품 검색 시스템
**재사용 + 확장**: Yahoo Finance 검색 로직 응용

#### 3.1 검색 기능
- **전체 텍스트 검색**: 제품명, 브랜드, 모델번호, 설명
- **카테고리별 필터링**: 대분류 → 중분류 → 소분류
- **고급 필터**:
  - 가격 범위
  - 제품 상태
  - 지역
  - 단종 연도
  - 재고 유무

#### 3.2 검색 결과 표시
- 그리드/리스트 뷰 전환
- 정렬: 최신순, 가격 낮은순, 가격 높은순, 인기순
- 페이지네이션 (무한 스크롤)
- 검색 결과 카운트

#### 3.3 AI 추천 시스템 (향후 확장)
- 유사 제품 추천
- 대체 제품 제안
- 사용자 검색 기록 기반 추천

### 4. 제품 상세 페이지
**신규 기능**

#### 4.1 제품 정보 표시
- 제품 이미지 갤러리 (확대 기능)
- 제품 상세 정보 테이블
- 판매자 정보 카드
- 가격 정보 (정가, 할인가)
- 재고 상태 표시

#### 4.2 연락/문의 기능
- **문의하기 버튼**:
  - 로그인 사용자: 판매자에게 직접 연락 (전화, 이메일, 채팅)
  - 비로그인 사용자: 로그인 유도

- **문의 폼**:
  - 구매 희망 수량
  - 문의 내용
  - 연락받을 방법 (전화, 이메일, 카카오톡)

- **찜하기/관심상품**: 나중에 다시 보기

#### 4.3 가격 협상 시스템 (향후)
- 가격 제안 기능
- 판매자 수락/거절
- 협상 히스토리

### 5. 대시보드 (판매자)
**재사용 컴포넌트**: AI 헤지펀드 대시보드 구조

#### 5.1 판매자 대시보드
- 등록 제품 목록
- 문의 현황 (신규, 답변 대기, 완료)
- 판매 통계 (조회수, 문의수, 거래 완료)
- 제품 수정/삭제/재등록

#### 5.2 구매자 대시보드
- 관심 상품 목록
- 문의 내역
- 검색 기록
- 최근 본 상품

### 6. 알림 시스템
**확장 기능**

- 신규 문의 알림 (이메일, SMS, 푸시)
- 가격 인하 알림
- 관심 상품 재입고 알림
- 채팅 메시지 알림

---

## 🏗️ 기술 스택 (재사용 기반)

### Backend
**재사용**:
- **FastAPI**: REST API 서버 (`simple_web_api.py` 구조 활용)
- **Python 3.11+**: 비동기 처리, 타입 힌팅
- **Pydantic**: 데이터 모델 검증
- **JWT**: 인증/인가
- **Poetry**: 패키지 관리

**신규 추가**:
- **SQLAlchemy**: ORM (PostgreSQL 연동)
- **Alembic**: DB 마이그레이션
- **PostgreSQL**: 프로덕션 데이터베이스
- **Redis**: 캐싱, 세션 관리
- **Celery**: 비동기 작업 (이메일, 이미지 처리)

### Frontend
**재사용**:
- **HTML/CSS/JavaScript** (바닐라): `web/index.html` 구조
- **Chart.js**: 통계 시각화 (판매자 대시보드)
- **Axios**: HTTP 클라이언트
- **다크 테마**: 기존 CSS 변수 시스템

**신규 추가**:
- **Alpine.js** (선택): 경량 반응형 UI (React 대안)
- **TailwindCSS** (선택): 유틸리티 CSS (기존 커스텀 CSS와 병행)
- **Swiper.js**: 이미지 갤러리/슬라이더

### Infrastructure
**재사용**:
- **Docker**: 컨테이너화
- **Uvicorn**: ASGI 서버
- **환경변수 관리**: `.env` 파일

**신규 추가**:
- **Nginx**: 리버스 프록시, 정적 파일 서빙
- **PostgreSQL**: 데이터베이스
- **Redis**: 캐시/세션
- **Cloudflare R2/AWS S3**: 이미지 스토리지
- **Docker Compose**: 멀티 컨테이너 오케스트레이션

### 개발 도구
**재사용**:
- **Black**: 코드 포매터 (line-length 420)
- **isort**: Import 정렬
- **Playwright**: E2E 테스트
- **Poetry**: 의존성 관리

---

## 📊 데이터 모델

### 1. User (사용자)
```python
class User(BaseModel):
    id: int
    email: str
    username: str
    hashed_password: str
    user_type: str  # "buyer", "seller", "admin"
    is_verified: bool
    phone_number: Optional[str]
    created_at: datetime
    updated_at: datetime
```

### 2. Seller (판매자)
```python
class Seller(BaseModel):
    id: int
    user_id: int  # FK to User
    company_name: str
    business_number: Optional[str]  # 사업자번호
    address: str
    region: str  # 지역
    is_verified: bool  # 인증 판매자
    rating: float  # 평점
    total_sales: int
    created_at: datetime
```

### 3. Product (제품)
```python
class Product(BaseModel):
    id: int
    seller_id: int  # FK to Seller
    category_id: int  # FK to Category

    # 기본 정보
    product_name: str
    brand: str
    model_number: str
    discontinued_year: int
    discontinued_month: Optional[int]

    # 상태 및 재고
    condition: str  # "new", "like_new", "good", "fair", "for_parts"
    quantity: int
    price: float
    is_negotiable: bool

    # 상세 정보
    description: Optional[str]
    specifications: Optional[Dict]  # JSON 필드
    origin: Optional[str]

    # 이미지
    images: List[str]  # 이미지 URL 배열
    thumbnail: str

    # 상태
    status: str  # "active", "sold", "reserved", "deleted"
    view_count: int
    inquiry_count: int

    # 메타
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
```

### 4. Category (카테고리)
```python
class Category(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]  # 상위 카테고리
    level: int  # 계층 (1: 대분류, 2: 중분류, 3: 소분류)
    order: int
```

### 5. Inquiry (문의)
```python
class Inquiry(BaseModel):
    id: int
    product_id: int  # FK to Product
    buyer_id: int  # FK to User
    seller_id: int  # FK to Seller

    # 문의 내용
    quantity: int
    message: str
    contact_method: str  # "phone", "email", "kakao"

    # 상태
    status: str  # "pending", "answered", "closed"

    # 응답
    seller_response: Optional[str]
    responded_at: Optional[datetime]

    created_at: datetime
```

### 6. Favorite (관심상품)
```python
class Favorite(BaseModel):
    id: int
    user_id: int  # FK to User
    product_id: int  # FK to Product
    created_at: datetime
```

---

## 🔌 API 엔드포인트 설계

### 인증 (Auth)
```
POST   /api/auth/register        # 회원가입
POST   /api/auth/login           # 로그인
POST   /api/auth/logout          # 로그아웃
GET    /api/auth/me              # 내 정보 조회
PUT    /api/auth/me              # 내 정보 수정
POST   /api/auth/verify-email    # 이메일 인증
```

### 제품 (Products)
```
GET    /api/products             # 제품 목록 조회 (검색, 필터, 정렬)
GET    /api/products/:id         # 제품 상세 조회
POST   /api/products             # 제품 등록 (판매자)
PUT    /api/products/:id         # 제품 수정 (판매자)
DELETE /api/products/:id         # 제품 삭제 (판매자)
POST   /api/products/:id/images  # 이미지 업로드
```

### 카테고리 (Categories)
```
GET    /api/categories           # 카테고리 트리 조회
GET    /api/categories/:id       # 특정 카테고리 제품 조회
```

### 문의 (Inquiries)
```
GET    /api/inquiries            # 내 문의 목록 (구매자/판매자)
GET    /api/inquiries/:id        # 문의 상세
POST   /api/inquiries            # 문의 등록
PUT    /api/inquiries/:id        # 문의 응답 (판매자)
DELETE /api/inquiries/:id        # 문의 삭제
```

### 관심상품 (Favorites)
```
GET    /api/favorites            # 관심상품 목록
POST   /api/favorites            # 관심상품 추가
DELETE /api/favorites/:id        # 관심상품 제거
```

### 판매자 (Sellers)
```
GET    /api/sellers/:id          # 판매자 정보 조회
GET    /api/sellers/:id/products # 판매자 제품 목록
POST   /api/sellers/verify       # 판매자 인증 신청
```

### 대시보드 (Dashboard)
```
GET    /api/dashboard/seller     # 판매자 대시보드
GET    /api/dashboard/buyer      # 구매자 대시보드
GET    /api/dashboard/stats      # 통계 정보
```

---

## 🎨 UI/UX 설계

### 재사용 디자인 시스템
**AI 헤지펀드의 다크 테마 CSS 변수**:
```css
:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #131722;
    --bg-card: #1e222d;
    --bg-hover: #2a2e39;
    --text-primary: #d1d4dc;
    --text-secondary: #868b98;
    --text-bright: #ffffff;
    --accent-green: #26a69a;
    --accent-red: #ef5350;
    --accent-blue: #2962ff;
    --accent-yellow: #ffb300;
    --border-color: #2a2e39;
}
```

### 페이지 구조

#### 1. 메인 페이지 (홈)
```
┌─────────────────────────────────────────────┐
│  [로고]  검색창        [로그인] [회원가입]   │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  대형 검색 박스                       │ │
│  │  "찾고 계신 단종제품을 검색하세요"    │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  인기 카테고리: [전자제품] [가전] [부품]   │
│                                             │
│  최근 등록 제품                             │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐              │
│  │제품│ │제품│ │제품│ │제품│              │
│  └────┘ └────┘ └────┘ └────┘              │
│                                             │
└─────────────────────────────────────────────┘
```

#### 2. 검색 결과 페이지
```
┌───────────────┬─────────────────────────────┐
│ 필터          │  검색결과: 123건             │
│               ├─────────────────────────────┤
│ [카테고리]    │  ┌─────────────────────┐   │
│  ㄴ 전자제품  │  │ [썸네일] 제품명      │   │
│  ㄴ 가전      │  │ 가격: 50,000원       │   │
│               │  │ 지역: 서울           │   │
│ [가격]        │  └─────────────────────┘   │
│  ○ 전체      │                             │
│  ○ ~10만원   │  ┌─────────────────────┐   │
│               │  │ [썸네일] 제품명      │   │
│ [상태]        │  └─────────────────────┘   │
│  ☑ 신품      │                             │
│  ☐ 중고      │  [더보기 버튼]              │
│               │                             │
└───────────────┴─────────────────────────────┘
```

#### 3. 제품 상세 페이지
```
┌─────────────────────────────────────────────┐
│  제품명 / 브랜드                             │
├─────────────────┬───────────────────────────┤
│                 │  가격: 50,000원           │
│  [이미지 갤러리] │  상태: 신품               │
│  ┌───────────┐  │  재고: 3개                │
│  │   메인    │  │                           │
│  │   이미지  │  │  [문의하기] [찜하기]      │
│  └───────────┘  │                           │
│  [◀] [▶]       │  판매자 정보:              │
│                 │  ┌─────────────────┐      │
│                 │  │ 상호명          │      │
│                 │  │ 지역: 서울      │      │
│                 │  │ 평점: ★★★★☆   │      │
│                 │  └─────────────────┘      │
├─────────────────┴───────────────────────────┤
│  상세 설명                                   │
│  제품 스펙                                   │
│  제조사: OO전자                              │
│  모델번호: ABC-123                           │
│  단종: 2023년 3월                            │
└─────────────────────────────────────────────┘
```

#### 4. 판매자 대시보드
```
┌─────────────────────────────────────────────┐
│  [내 제품] [문의관리] [통계] [설정]          │
├─────────────────────────────────────────────┤
│  요약 통계                                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │등록제품│ │조회수│ │문의수│ │판매완료│       │
│  │  24   │ │ 1.2K │ │  45  │ │  12   │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                             │
│  최근 문의 (답변 대기 중)                    │
│  ┌───────────────────────────────────────┐ │
│  │ 제품명: ABC-123                        │ │
│  │ 문의: 수량 10개 구매 가능한가요?       │ │
│  │ [답변하기]                             │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  내 제품 목록                                │
│  [+ 신규 제품 등록]                         │
│  ┌─────────────────────────────────────┐   │
│  │ [이미지] 제품명 | 가격 | 재고 | [수정] [삭제] │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🚀 개발 로드맵

### Phase 1: MVP 개발 (4주)
**Week 1-2: Backend 기반 구축**
- [ ] 프로젝트 셋업 (Poetry, Docker, PostgreSQL)
- [ ] 데이터 모델 설계 및 마이그레이션
- [ ] JWT 인증 시스템 (재사용)
- [ ] User/Seller 모델 및 API
- [ ] 제품 등록/조회 API (CRUD)

**Week 3: Frontend 핵심 페이지**
- [ ] 다크 테마 CSS 변수 이식
- [ ] 메인 페이지 (검색 인터페이스)
- [ ] 제품 목록 페이지 (필터, 정렬)
- [ ] 제품 상세 페이지
- [ ] 제품 등록 폼 (판매자)

**Week 4: 통합 및 테스트**
- [ ] 이미지 업로드 시스템
- [ ] 문의 시스템
- [ ] 판매자 대시보드
- [ ] Playwright E2E 테스트
- [ ] 배포 준비 (Docker Compose)

### Phase 2: 고도화 (4주)
- [ ] 고급 검색 필터
- [ ] 관심상품 시스템
- [ ] 알림 시스템 (이메일, SMS)
- [ ] 통계 대시보드 (Chart.js)
- [ ] 판매자 인증 시스템
- [ ] 리뷰/평점 시스템

### Phase 3: 확장 기능 (진행형)
- [ ] AI 추천 시스템 (유사 제품)
- [ ] 가격 협상 시스템
- [ ] 채팅 기능 (실시간)
- [ ] 모바일 최적화
- [ ] SEO 최적화
- [ ] 다국어 지원

---

## 📝 환경 설정 파일

### `.env` 예시
```env
# 애플리케이션
APP_NAME=단종제품 검색 플랫폼
APP_ENV=development
APP_DEBUG=true
APP_URL=http://192.168.1.3:8888

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/discontinued_products
REDIS_URL=redis://localhost:6379/0

# JWT 인증
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 관리자 계정
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_admin_password

# 이미지 스토리지 (Cloudflare R2)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=product-images

# 이메일 (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourplatform.com

# SMS (알림톡 - 선택)
SMS_API_KEY=your-sms-api-key
SMS_SENDER=01012345678

# 외부 API (선택)
GOOGLE_ANALYTICS_ID=UA-XXXXX-X
SENTRY_DSN=your-sentry-dsn
```

### `pyproject.toml` 주요 의존성
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.25"
alembic = "^1.13.1"
asyncpg = "^0.29.0"  # PostgreSQL async driver
pydantic = {extras = ["email"], version = "^2.5.3"}
pydantic-settings = "^2.1.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"  # 파일 업로드
pillow = "^10.2.0"  # 이미지 처리
boto3 = "^1.34.27"  # AWS S3/R2
redis = {extras = ["hiredis"], version = "^5.0.1"}
celery = "^5.3.6"  # 비동기 작업
aiosmtplib = "^3.0.1"  # 이메일 전송

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
black = "^24.1.1"
isort = "^5.13.2"
playwright = "^1.41.0"
```

---

## 🔒 보안 고려사항

### 1. 인증/인가
- JWT 토큰 안전한 저장 (httpOnly 쿠키)
- 비밀번호 bcrypt 해싱
- 이메일 인증 필수
- CSRF 토큰

### 2. 데이터 보호
- SQL Injection 방지 (ORM 사용)
- XSS 방지 (입력 검증, 출력 이스케이프)
- 이미지 업로드 파일 타입 검증
- 사업자번호 등 민감정보 암호화

### 3. API 보호
- Rate Limiting (fastapi-limiter)
- CORS 설정
- API 키 관리

---

## 📊 성능 목표

### 응답 시간
- 메인 페이지 로딩: < 1초
- 검색 결과: < 2초
- 제품 상세: < 1.5초
- 이미지 업로드: < 5초 (10MB)

### 동시 사용자
- 초기: 100명
- 6개월: 1,000명
- 1년: 5,000명

### 데이터베이스
- 제품: 100,000개 (1년 목표)
- 사용자: 10,000명 (1년 목표)
- 이미지: 1TB (클라우드 스토리지)

---

## 📈 비즈니스 메트릭

### 핵심 지표 (KPI)
1. **DAU/MAU**: 일간/월간 활성 사용자
2. **제품 등록 수**: 일일 신규 제품
3. **문의 전환율**: 조회 → 문의 비율
4. **거래 성사율**: 문의 → 거래 완료 비율
5. **판매자 활성도**: 활동 판매자 비율
6. **검색 성공률**: 검색 → 클릭 비율

### 수익 모델 (향후)
- 프리미엄 판매자 등록 (월 구독)
- 제품 노출 광고 (스폰서드 제품)
- 거래 수수료 (판매가의 3-5%)
- 배너 광고

---

## 🧪 테스트 전략

### 1. 단위 테스트 (Pytest)
- 모델 메서드
- API 엔드포인트
- 비즈니스 로직

### 2. E2E 테스트 (Playwright)
**재사용**: AI 헤지펀드의 테스트 패턴
- 사용자 회원가입 플로우
- 제품 등록 플로우
- 검색 및 문의 플로우
- 판매자 대시보드 시나리오

### 3. 성능 테스트
- Locust/K6로 부하 테스트
- 데이터베이스 쿼리 최적화

---

## 🚧 마이그레이션 체크리스트

### AI 헤지펀드 → 단종제품 플랫폼

#### 재사용 가능
- [x] FastAPI 서버 구조 (`simple_web_api.py`)
- [x] JWT 인증 시스템
- [x] 다크 테마 CSS (`web/index.html`)
- [x] Chart.js 통계 시각화
- [x] Playwright E2E 테스트 프레임워크
- [x] Docker 컨테이너화
- [x] Poetry 패키지 관리
- [x] Black/isort 코드 스타일

#### 새로 개발 필요
- [ ] PostgreSQL + SQLAlchemy ORM
- [ ] 제품/카테고리/문의 모델
- [ ] 이미지 업로드 시스템
- [ ] 검색/필터 로직
- [ ] 판매자/구매자 대시보드
- [ ] 이메일/SMS 알림

#### 제거/미사용
- ~~Yahoo Finance 연동~~
- ~~AI 에이전트 시스템~~
- ~~LangGraph 워크플로우~~
- ~~백테스팅 엔진~~
- ~~실시간 거래 시스템~~

---

## 📞 접속 정보

### 개발 환경
- **URL**: http://192.168.1.3:8888 (네트워크 접속 권장)
- **로컬**: http://127.0.0.1:8888
- **API 문서**: http://192.168.1.3:8888/docs (Swagger UI)

### 초기 관리자 계정
- **사용자명**: admin
- **비밀번호**: discontinued2024!

---

## 📚 참고 자료

### 레퍼런스 사이트
- **중고나라**: 커뮤니티 기반 거래
- **당근마켓**: 지역 기반 거래
- **알리바바**: B2B 제품 검색
- **G마켓/옥션**: 카테고리 시스템

### 기술 문서
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/
- Chart.js: https://www.chartjs.org/

---

## ✅ 다음 단계

1. **PRD 검토 및 승인**
2. **프로젝트 셋업**: 새 레포지토리 생성, 초기 코드 구조
3. **데이터베이스 스키마 설계**: ERD 작성
4. **와이어프레임 작성**: Figma/Sketch (선택)
5. **Sprint 1 시작**: 인증 시스템 + 제품 CRUD

---

**작성일**: 2025-01-06
**버전**: 1.0
**작성자**: Claude Code
**기반 프로젝트**: AI 헤지펀드 시스템
