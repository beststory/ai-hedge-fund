-- ===================================================================
-- 예측 시장 (Prediction Market) 데이터베이스 스키마
-- Polymarket 스타일 시스템
-- ===================================================================

-- 1. 예측 주제 테이블
CREATE TABLE IF NOT EXISTS prediction_topics (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,                          -- 예측 주제 제목
    description TEXT,                             -- 상세 설명
    category TEXT NOT NULL,                       -- 카테고리: stock, economy, culture, tech, politics
    question_type TEXT DEFAULT 'binary',          -- binary (Yes/No) 또는 probability (0-100%)

    -- 타임라인
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deadline TIMESTAMPTZ NOT NULL,                -- 예측 마감일
    resolution_date TIMESTAMPTZ,                  -- 실제 결과 확정일

    -- 결과
    status TEXT DEFAULT 'open',                   -- open, closed, resolved, cancelled
    actual_outcome TEXT,                          -- 실제 결과: 'yes', 'no', 또는 숫자
    resolution_notes TEXT,                        -- 결과 판정 근거

    -- 메타데이터
    tags TEXT[],                                  -- 태그 (예: ['AAPL', 'tech', 'earnings'])
    related_tickers TEXT[],                       -- 관련 종목 코드
    data_source TEXT,                             -- 결과 검증 데이터 출처

    created_by TEXT,                              -- 생성자 (user_id 또는 'system')
    view_count INTEGER DEFAULT 0,
    prediction_count INTEGER DEFAULT 0,

    CONSTRAINT valid_status CHECK (status IN ('open', 'closed', 'resolved', 'cancelled')),
    CONSTRAINT valid_category CHECK (category IN ('stock', 'economy', 'culture', 'tech', 'politics', 'other'))
);

-- 인덱스
CREATE INDEX idx_topics_status ON prediction_topics(status);
CREATE INDEX idx_topics_category ON prediction_topics(category);
CREATE INDEX idx_topics_deadline ON prediction_topics(deadline);
CREATE INDEX idx_topics_tags ON prediction_topics USING GIN(tags);

-- 2. 사용자 예측 테이블
CREATE TABLE IF NOT EXISTS user_predictions (
    id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES prediction_topics(id) ON DELETE CASCADE,

    -- 예측자 정보
    user_id TEXT,                                 -- Supabase Auth user_id (NULL = anonymous)
    user_name TEXT,                               -- 표시 이름
    predictor_type TEXT DEFAULT 'human',          -- 'human' 또는 'ai_agent'
    agent_name TEXT,                              -- AI 에이전트 이름 (예: 'warren_buffett')

    -- 예측 내용
    prediction_value NUMERIC,                     -- 확률(0-100) 또는 이진값(0/1)
    prediction_text TEXT,                         -- Yes/No 등 텍스트 응답
    confidence_level TEXT,                        -- 'low', 'medium', 'high'
    reasoning TEXT,                               -- 예측 근거/이유

    -- 시간
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 메타데이터
    data_sources TEXT[],                          -- 사용한 데이터 출처

    CONSTRAINT valid_predictor_type CHECK (predictor_type IN ('human', 'ai_agent')),
    CONSTRAINT valid_confidence CHECK (confidence_level IN ('low', 'medium', 'high')),
    CONSTRAINT valid_prediction_value CHECK (prediction_value >= 0 AND prediction_value <= 100)
);

-- 인덱스
CREATE INDEX idx_predictions_topic ON user_predictions(topic_id);
CREATE INDEX idx_predictions_user ON user_predictions(user_id);
CREATE INDEX idx_predictions_type ON user_predictions(predictor_type);
CREATE INDEX idx_predictions_agent ON user_predictions(agent_name);
CREATE INDEX idx_predictions_created ON user_predictions(created_at);

-- 3. 예측 정확도 추적 테이블
CREATE TABLE IF NOT EXISTS prediction_accuracy (
    id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES prediction_topics(id) ON DELETE CASCADE,
    prediction_id BIGINT NOT NULL REFERENCES user_predictions(id) ON DELETE CASCADE,

    -- 정확도 메트릭
    brier_score NUMERIC,                          -- Brier Score (0=완벽, 1=최악)
    log_score NUMERIC,                            -- Logarithmic Score
    accuracy_percentage NUMERIC,                  -- 정확도 (%)

    -- 결과 비교
    predicted_value NUMERIC,
    actual_value NUMERIC,
    error_margin NUMERIC,

    -- 시간
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(topic_id, prediction_id)
);

-- 인덱스
CREATE INDEX idx_accuracy_topic ON prediction_accuracy(topic_id);
CREATE INDEX idx_accuracy_prediction ON prediction_accuracy(prediction_id);
CREATE INDEX idx_accuracy_brier ON prediction_accuracy(brier_score);

-- 4. 사용자 성과 요약 테이블
CREATE TABLE IF NOT EXISTS predictor_performance (
    id BIGSERIAL PRIMARY KEY,

    -- 예측자 정보
    user_id TEXT,
    agent_name TEXT,
    predictor_type TEXT NOT NULL,

    -- 성과 지표
    total_predictions INTEGER DEFAULT 0,
    resolved_predictions INTEGER DEFAULT 0,
    avg_brier_score NUMERIC,
    avg_accuracy NUMERIC,

    -- 카테고리별 성과
    category_stats JSONB DEFAULT '{}',            -- 카테고리별 정확도

    -- 순위
    global_rank INTEGER,
    category_rank JSONB DEFAULT '{}',

    -- 시간
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_predictor_type_perf CHECK (predictor_type IN ('human', 'ai_agent')),
    UNIQUE(user_id, agent_name, predictor_type)
);

-- 인덱스
CREATE INDEX idx_performance_user ON predictor_performance(user_id);
CREATE INDEX idx_performance_agent ON predictor_performance(agent_name);
CREATE INDEX idx_performance_rank ON predictor_performance(global_rank);

-- 5. 커뮤니티 컨센서스 뷰 (실시간 집계)
CREATE OR REPLACE VIEW community_consensus AS
SELECT
    t.id as topic_id,
    t.title,
    t.category,
    t.status,
    t.deadline,

    -- 전체 예측 통계
    COUNT(p.id) as total_predictions,
    AVG(p.prediction_value) as avg_prediction,
    STDDEV(p.prediction_value) as prediction_stddev,

    -- 인간 vs AI 비교
    AVG(CASE WHEN p.predictor_type = 'human' THEN p.prediction_value END) as human_avg,
    AVG(CASE WHEN p.predictor_type = 'ai_agent' THEN p.prediction_value END) as ai_avg,

    COUNT(CASE WHEN p.predictor_type = 'human' THEN 1 END) as human_count,
    COUNT(CASE WHEN p.predictor_type = 'ai_agent' THEN 1 END) as ai_count,

    -- 최근 추세
    MAX(p.created_at) as last_prediction_at

FROM prediction_topics t
LEFT JOIN user_predictions p ON t.id = p.topic_id
WHERE t.status = 'open'
GROUP BY t.id, t.title, t.category, t.status, t.deadline;

-- 6. AI 에이전트별 컨센서스 뷰
CREATE OR REPLACE VIEW ai_agent_consensus AS
SELECT
    t.id as topic_id,
    t.title,
    p.agent_name,
    p.prediction_value,
    p.confidence_level,
    p.reasoning,
    p.created_at,
    perf.avg_accuracy as agent_historical_accuracy
FROM prediction_topics t
JOIN user_predictions p ON t.id = p.topic_id
LEFT JOIN predictor_performance perf ON p.agent_name = perf.agent_name
WHERE p.predictor_type = 'ai_agent'
  AND t.status = 'open';

-- 7. 투자 시그널 생성 뷰
CREATE OR REPLACE VIEW investment_signals AS
SELECT
    t.id as topic_id,
    t.title,
    t.category,
    t.related_tickers,

    -- 예측 집계
    AVG(p.prediction_value) as consensus_probability,
    COUNT(p.id) as prediction_count,

    -- 신뢰도 가중 평균 (confidence 고려)
    AVG(CASE
        WHEN p.confidence_level = 'high' THEN p.prediction_value * 1.5
        WHEN p.confidence_level = 'medium' THEN p.prediction_value * 1.0
        WHEN p.confidence_level = 'low' THEN p.prediction_value * 0.5
    END) as confidence_weighted_avg,

    -- 시그널 강도
    CASE
        WHEN AVG(p.prediction_value) > 70 THEN 'strong_bullish'
        WHEN AVG(p.prediction_value) > 55 THEN 'bullish'
        WHEN AVG(p.prediction_value) < 30 THEN 'strong_bearish'
        WHEN AVG(p.prediction_value) < 45 THEN 'bearish'
        ELSE 'neutral'
    END as signal_strength,

    t.deadline

FROM prediction_topics t
JOIN user_predictions p ON t.id = p.topic_id
WHERE t.status = 'open'
  AND t.related_tickers IS NOT NULL
  AND t.category IN ('stock', 'economy')
GROUP BY t.id, t.title, t.category, t.related_tickers, t.deadline;

-- ===================================================================
-- 헬퍼 함수
-- ===================================================================

-- Brier Score 계산 함수
CREATE OR REPLACE FUNCTION calculate_brier_score(
    predicted_prob NUMERIC,
    actual_outcome NUMERIC
) RETURNS NUMERIC AS $$
BEGIN
    -- Brier Score = (predicted - actual)^2
    -- 0 = 완벽한 예측, 1 = 최악의 예측
    RETURN POWER(predicted_prob / 100.0 - actual_outcome, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 예측 정확도 업데이트 함수 (트리거용)
CREATE OR REPLACE FUNCTION update_prediction_accuracy()
RETURNS TRIGGER AS $$
BEGIN
    -- 주제가 resolved 상태로 변경되면 모든 예측의 정확도 계산
    IF NEW.status = 'resolved' AND OLD.status != 'resolved' THEN
        INSERT INTO prediction_accuracy (topic_id, prediction_id, predicted_value, actual_value, brier_score, accuracy_percentage)
        SELECT
            p.topic_id,
            p.id,
            p.prediction_value,
            CASE
                WHEN NEW.actual_outcome = 'yes' THEN 100
                WHEN NEW.actual_outcome = 'no' THEN 0
                ELSE NEW.actual_outcome::NUMERIC
            END as actual_val,
            calculate_brier_score(
                p.prediction_value,
                CASE
                    WHEN NEW.actual_outcome = 'yes' THEN 1
                    WHEN NEW.actual_outcome = 'no' THEN 0
                    ELSE NEW.actual_outcome::NUMERIC / 100.0
                END
            ),
            100 - ABS(p.prediction_value -
                CASE
                    WHEN NEW.actual_outcome = 'yes' THEN 100
                    WHEN NEW.actual_outcome = 'no' THEN 0
                    ELSE NEW.actual_outcome::NUMERIC
                END
            )
        FROM user_predictions p
        WHERE p.topic_id = NEW.id
        ON CONFLICT (topic_id, prediction_id) DO NOTHING;

        -- 성과 요약 업데이트
        PERFORM update_predictor_performance();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS trigger_update_accuracy ON prediction_topics;
CREATE TRIGGER trigger_update_accuracy
    AFTER UPDATE ON prediction_topics
    FOR EACH ROW
    EXECUTE FUNCTION update_prediction_accuracy();

-- 예측자 성과 업데이트 함수
CREATE OR REPLACE FUNCTION update_predictor_performance()
RETURNS void AS $$
BEGIN
    -- 인간 사용자 성과 업데이트
    INSERT INTO predictor_performance (user_id, predictor_type, total_predictions, resolved_predictions, avg_brier_score, avg_accuracy)
    SELECT
        p.user_id,
        'human',
        COUNT(*),
        COUNT(a.id),
        AVG(a.brier_score),
        AVG(a.accuracy_percentage)
    FROM user_predictions p
    LEFT JOIN prediction_accuracy a ON p.id = a.prediction_id
    WHERE p.predictor_type = 'human' AND p.user_id IS NOT NULL
    GROUP BY p.user_id
    ON CONFLICT (user_id, agent_name, predictor_type)
    DO UPDATE SET
        total_predictions = EXCLUDED.total_predictions,
        resolved_predictions = EXCLUDED.resolved_predictions,
        avg_brier_score = EXCLUDED.avg_brier_score,
        avg_accuracy = EXCLUDED.avg_accuracy,
        updated_at = NOW();

    -- AI 에이전트 성과 업데이트
    INSERT INTO predictor_performance (agent_name, predictor_type, total_predictions, resolved_predictions, avg_brier_score, avg_accuracy)
    SELECT
        p.agent_name,
        'ai_agent',
        COUNT(*),
        COUNT(a.id),
        AVG(a.brier_score),
        AVG(a.accuracy_percentage)
    FROM user_predictions p
    LEFT JOIN prediction_accuracy a ON p.id = a.prediction_id
    WHERE p.predictor_type = 'ai_agent' AND p.agent_name IS NOT NULL
    GROUP BY p.agent_name
    ON CONFLICT (user_id, agent_name, predictor_type)
    DO UPDATE SET
        total_predictions = EXCLUDED.total_predictions,
        resolved_predictions = EXCLUDED.resolved_predictions,
        avg_brier_score = EXCLUDED.avg_brier_score,
        avg_accuracy = EXCLUDED.avg_accuracy,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ===================================================================
-- 샘플 데이터
-- ===================================================================

-- 예제 예측 주제 1: 주식 관련
INSERT INTO prediction_topics (title, description, category, question_type, deadline, tags, related_tickers, data_source)
VALUES (
    'AAPL이 2025년 Q1 실적 발표에서 매출 예상치를 상회할까?',
    'Apple의 2025년 1분기 실적 발표가 3월 예정입니다. 애널리스트 컨센서스는 $950억입니다.',
    'stock',
    'binary',
    '2025-03-31 23:59:59+00',
    ARRAY['AAPL', 'earnings', 'tech'],
    ARRAY['AAPL'],
    'yahoo_finance'
);

-- 예제 예측 주제 2: 경제 지표
INSERT INTO prediction_topics (title, description, category, question_type, deadline, tags, data_source)
VALUES (
    '2025년 12월 미국 실업률이 4% 이하일까?',
    '현재 실업률은 3.7%입니다. FED의 금리 정책과 경기 전망이 영향을 미칠 것입니다.',
    'economy',
    'binary',
    '2025-12-31 23:59:59+00',
    ARRAY['unemployment', 'economy', 'fed'],
    'fred'
);

-- 예제 예측 주제 3: 문화 트렌드
INSERT INTO prediction_topics (title, description, category, question_type, deadline, tags, related_tickers)
VALUES (
    'K-POP이 2025년 Billboard Hot 100 연간 차트에서 Top 10에 진입할까?',
    '한국 문화 트렌드와 글로벌 음악 시장의 변화를 예측합니다.',
    'culture',
    'binary',
    '2025-12-31 23:59:59+00',
    ARRAY['kpop', 'culture', 'entertainment'],
    ARRAY['035420.KS', '041510.KS']  -- NAVER, SM엔터
);

-- ===================================================================
-- RLS (Row Level Security) 정책
-- ===================================================================

-- RLS 활성화
ALTER TABLE prediction_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE prediction_accuracy ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictor_performance ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 예측 주제 읽기 가능
CREATE POLICY "주제는 누구나 볼 수 있음"
    ON prediction_topics FOR SELECT
    USING (true);

-- 인증된 사용자만 주제 생성 가능
CREATE POLICY "인증된 사용자만 주제 생성"
    ON prediction_topics FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- 모든 사용자가 예측 읽기 가능
CREATE POLICY "예측은 누구나 볼 수 있음"
    ON user_predictions FOR SELECT
    USING (true);

-- 인증된 사용자만 예측 제출
CREATE POLICY "인증된 사용자만 예측 제출"
    ON user_predictions FOR INSERT
    WITH CHECK (auth.role() = 'authenticated' OR predictor_type = 'ai_agent');

-- 자신의 예측만 수정 가능
CREATE POLICY "자신의 예측만 수정"
    ON user_predictions FOR UPDATE
    USING (auth.uid()::text = user_id);

COMMENT ON TABLE prediction_topics IS '예측 주제 관리 테이블';
COMMENT ON TABLE user_predictions IS '사용자 및 AI 에이전트 예측 저장';
COMMENT ON TABLE prediction_accuracy IS '예측 정확도 추적 (Brier Score 등)';
COMMENT ON TABLE predictor_performance IS '예측자별 성과 요약 (순위, 평균 정확도)';
COMMENT ON VIEW community_consensus IS '커뮤니티 컨센서스 실시간 집계';
COMMENT ON VIEW investment_signals IS '예측 데이터 기반 투자 시그널 생성';
