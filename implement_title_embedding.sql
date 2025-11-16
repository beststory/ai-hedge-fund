-- 제목 임베딩 컬럼 추가
ALTER TABLE investment_insights
ADD COLUMN IF NOT EXISTS title_embedding vector(768);

-- 제목 임베딩 인덱스 생성
CREATE INDEX IF NOT EXISTS investment_insights_title_embedding_idx
ON investment_insights
USING hnsw (title_embedding vector_cosine_ops);

-- 하이브리드 검색 RPC 함수 생성
CREATE OR REPLACE FUNCTION match_insights_hybrid(
    query_embedding vector(768),
    match_count int,
    use_title_weight float DEFAULT 0.3  -- 제목 가중치
)
RETURNS TABLE (
    id int,
    title text,
    content text,
    sector text,
    sentiment text,
    keywords text[],
    url text,
    date text,
    similarity float
)
AS $$
BEGIN
    -- title_embedding이 있으면 하이브리드 검색, 없으면 content 검색만
    RETURN QUERY
    SELECT
        investment_insights.id,
        investment_insights.title,
        investment_insights.content,
        investment_insights.sector,
        investment_insights.sentiment,
        investment_insights.keywords,
        investment_insights.url,
        investment_insights.date,
        CASE
            WHEN investment_insights.title_embedding IS NOT NULL THEN
                -- 하이브리드: 제목 유사도와 내용 유사도를 가중 평균
                (1 - (investment_insights.title_embedding <=> query_embedding)) * use_title_weight +
                (1 - (investment_insights.embedding <=> query_embedding)) * (1 - use_title_weight)
            ELSE
                -- 기존 방식: 내용 유사도만
                1 - (investment_insights.embedding <=> query_embedding)
        END as similarity
    FROM investment_insights
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- 코멘트 추가
COMMENT ON COLUMN investment_insights.title_embedding IS '제목만의 임베딩 (짧은 쿼리 검색용)';
COMMENT ON FUNCTION match_insights_hybrid IS '하이브리드 검색: 제목 임베딩과 내용 임베딩을 결합';
