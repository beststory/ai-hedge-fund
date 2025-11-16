-- 시간 가중치를 적용한 하이브리드 검색 (Exponential Time Decay)

-- 기존 함수 삭제하고 새로 생성
DROP FUNCTION IF EXISTS match_insights_hybrid(vector, int, float, text);

-- 시간 가중치 + 단어 단위 텍스트 검색을 포함한 하이브리드 검색 함수
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
DECLARE
    words text[];
BEGIN
    -- 검색어를 공백으로 분리하여 단어 배열 생성
    words := string_to_array(trim(query_text), ' ');

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
                -- 1. 벡터 유사도 계산 (0~1점)
                (1 - (investment_insights.title_embedding <=> query_embedding)) * use_title_weight +
                (1 - (investment_insights.embedding <=> query_embedding)) * (1 - use_title_weight) +

                -- 2. 단어 단위 텍스트 매칭 보너스
                CASE
                    WHEN query_text != '' AND (
                        SELECT bool_and(investment_insights.title ILIKE '%' || word || '%')
                        FROM unnest(words) AS word
                        WHERE word != ''
                    ) THEN 0.15
                    WHEN query_text != '' AND (
                        SELECT bool_and(investment_insights.content ILIKE '%' || word || '%')
                        FROM unnest(words) AS word
                        WHERE word != ''
                    ) THEN 0.05
                    ELSE 0
                END +

                -- 3. 시간 가중치 (Exponential Time Decay)
                -- 최신 글일수록 높은 점수, 최대 +0.2점
                -- exp(-age_days / 60) 형태로 exponential decay
                -- 0일: +0.20, 30일: +0.12, 60일: +0.073, 180일: +0.010
                CASE
                    WHEN investment_insights.created_at IS NOT NULL THEN
                        0.2 * exp(-EXTRACT(EPOCH FROM (NOW() - investment_insights.created_at)) / (86400.0 * 60.0))
                    ELSE 0
                END
            ELSE
                -- 기존 방식: 내용 유사도만 (title_embedding이 없는 경우)
                1 - (investment_insights.embedding <=> query_embedding) +
                CASE
                    WHEN query_text != '' AND (
                        SELECT bool_and(investment_insights.title ILIKE '%' || word || '%')
                        FROM unnest(words) AS word
                        WHERE word != ''
                    ) THEN 0.15
                    WHEN query_text != '' AND (
                        SELECT bool_and(investment_insights.content ILIKE '%' || word || '%')
                        FROM unnest(words) AS word
                        WHERE word != ''
                    ) THEN 0.05
                    ELSE 0
                END +
                CASE
                    WHEN investment_insights.created_at IS NOT NULL THEN
                        0.2 * exp(-EXTRACT(EPOCH FROM (NOW() - investment_insights.created_at)) / (86400.0 * 60.0))
                    ELSE 0
                END
        END as similarity
    FROM investment_insights
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- 코멘트 추가
COMMENT ON FUNCTION match_insights_hybrid IS '
벡터 검색 + 단어 단위 텍스트 검색 + Exponential Time Decay:
- 벡터 유사도 (0~1점)
- 텍스트 매칭 보너스 (제목 +0.15, 내용 +0.05)
- 시간 가중치: 최신일수록 exponential하게 증가 (최대 +0.2점)
  - 0일: +0.200
  - 30일: +0.121
  - 60일: +0.073
  - 180일: +0.010
  - 365일: +0.002
내용 우선, 유사도가 비슷할 때만 최신 글 우선
';
