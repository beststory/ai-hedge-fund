-- API 캐시 테이블 생성
-- 1시간 TTL로 API 응답 캐싱하여 성능 개선

CREATE TABLE IF NOT EXISTS api_cache (
    cache_key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    ttl_seconds INTEGER DEFAULT 3600,  -- 기본 1시간 (3600초)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성 (updated_at으로 만료된 캐시 빠르게 찾기)
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

-- 캐시 통계 조회 뷰
CREATE OR REPLACE VIEW api_cache_stats AS
SELECT
    COUNT(*) as total_entries,
    COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '1 hour') as valid_entries,
    COUNT(*) FILTER (WHERE updated_at <= NOW() - INTERVAL '1 hour') as expired_entries,
    pg_size_pretty(pg_total_relation_size('api_cache')) as table_size
FROM api_cache;

COMMENT ON TABLE api_cache IS 'API 응답 캐시 테이블 (1시간 TTL)';
COMMENT ON COLUMN api_cache.cache_key IS '캐시 키 (API 엔드포인트 + 파라미터)';
COMMENT ON COLUMN api_cache.data IS '캐시된 JSON 데이터';
COMMENT ON COLUMN api_cache.updated_at IS '마지막 업데이트 시간';
COMMENT ON COLUMN api_cache.ttl_seconds IS 'TTL (초 단위)';
