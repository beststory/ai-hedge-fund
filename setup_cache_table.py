"""Supabase API 캐시 테이블 설정 스크립트"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("🔧 Supabase API 캐시 테이블 설정")
print("=" * 80)
print("\n다음 단계를 따라주세요:\n")

# Supabase 대시보드 URL
supabase_url = os.getenv("SUPABASE_URL", "http://localhost:8000")
print(f"1. Supabase Studio 접속: {supabase_url}")
print("   (또는 https://app.supabase.com 에서 프로젝트 선택)\n")

print("2. SQL Editor로 이동\n")

print("3. 아래 SQL을 복사하여 실행:\n")

sql = """
-- API 캐시 테이블 생성
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    ttl_seconds INTEGER DEFAULT 3600,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS api_cache_updated_at_idx ON api_cache(updated_at);

-- 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_api_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER api_cache_updated_at_trigger
BEFORE UPDATE ON api_cache
FOR EACH ROW
EXECUTE FUNCTION update_api_cache_updated_at();

-- 확인
SELECT 'API 캐시 테이블이 성공적으로 생성되었습니다!' as message;
"""

print("=" * 80)
print(sql)
print("=" * 80)
print("\n4. SQL 실행 후 '1 row returned' 메시지 확인\n")

print("✅ 완료되면 웹 서버가 자동으로 캐싱을 시작합니다!")
print("=" * 80)

# Python으로도 테이블 생성 시도 (Supabase Admin API 사용)
try:
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL", "http://localhost:8000")
    service_key = os.getenv("SERVICE_ROLE_KEY")

    if service_key:
        print("\n🔄 Python API로 테이블 생성 시도 중...\n")
        client = create_client(supabase_url, service_key)

        # 테이블 존재 여부 확인
        try:
            result = client.table("api_cache").select("*").limit(1).execute()
            print("✅ api_cache 테이블이 이미 존재합니다!")
        except Exception:
            print("⚠️ api_cache 테이블이 없습니다. 위의 SQL을 Supabase Studio에서 실행해주세요.")
    else:
        print("\n⚠️ SERVICE_ROLE_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 SERVICE_ROLE_KEY를 추가하세요.\n")

except Exception as e:
    print(f"\n❌ 테이블 확인 실패: {e}")
    print("   위의 SQL을 Supabase Studio에서 수동으로 실행해주세요.\n")
