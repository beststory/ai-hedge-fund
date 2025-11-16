-- match_insights 함수 수정: url과 date 필드 추가

DROP FUNCTION IF EXISTS match_insights(vector, int);

CREATE FUNCTION match_insights(query_embedding vector(768), match_count int)
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
  SELECT
    id,
    title,
    content,
    sector,
    sentiment,
    keywords,
    url,
    date,
    1 - (embedding <=> query_embedding) as similarity
  FROM investment_insights
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$ LANGUAGE sql;
