-- 벡터 검색 + 텍스트 검색 하이브리드 시스템

-- 기존 함수 삭제하고 새로 생성
DROP FUNCTION IF EXISTS match_insights_hybrid(vector, int, float);

-- 텍스트 검색을 포함한 하이브리드 검색 함수
CREATE OR REPLACE FUNCTION match_insights_hybrid(
    query_embedding vector(768),
    match_count int,
    use_title_weight float DEFAULT 0.3,
    query_text text DEFAULT ''
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
                -- 벡터 유사도 계산 (0~1점)
                (1 - (investment_insights.title_embedding <=> query_embedding)) * use_title_weight +
                (1 - (investment_insights.embedding <=> query_embedding)) * (1 - use_title_weight) +
                -- 텍스트 매칭 보너스 점수
                CASE
                    WHEN query_text != '' AND investment_insights.title ILIKE '%' || query_text || '%' THEN 0.15  -- 제목 매칭 보너스
                    WHEN query_text != '' AND investment_insights.content ILIKE '%' || query_text || '%' THEN 0.05  -- 내용 매칭 보너스
                    ELSE 0
                END
            ELSE
                -- 기존 방식: 내용 유사도만 (title_embedding이 없는 경우)
                1 - (investment_insights.embedding <=> query_embedding) +
                CASE
                    WHEN query_text != '' AND investment_insights.title ILIKE '%' || query_text || '%' THEN 0.15
                    WHEN query_text != '' AND investment_insights.content ILIKE '%' || query_text || '%' THEN 0.05
                    ELSE 0
                END
        END as similarity
    FROM investment_insights
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- 코멘트 추가
COMMENT ON FUNCTION match_insights_hybrid IS '벡터 검색 + 텍스트 검색 하이브리드: 벡터 유사도(0~1점) + 텍스트 매칭 보너스(제목 +0.15, 내용 +0.05)';
