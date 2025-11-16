-- AI 지능형 투자 분석 시스템 Supabase 스키마

-- 1. 블로그 백테스팅 결과 테이블
CREATE TABLE IF NOT EXISTS blog_backtest_results (
    id SERIAL PRIMARY KEY,
    blog_id INTEGER,
    insight_text TEXT,
    insight_date TIMESTAMP,
    prediction_topic VARCHAR(100),  -- 예: "삼성전자", "금리", "반도체"
    prediction_direction VARCHAR(20),  -- "상승", "하락", "중립"
    ticker VARCHAR(20),  -- 관련 종목
    actual_start_price NUMERIC,
    actual_end_price NUMERIC,
    actual_return_pct NUMERIC,
    correlation_score FLOAT,  -- -1.0 ~ 1.0
    confidence_level VARCHAR(20),  -- "높음", "중간", "낮음"
    success BOOLEAN,
    test_period_months INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_correlation CHECK (correlation_score >= -1.0 AND correlation_score <= 1.0),
    CONSTRAINT valid_confidence CHECK (confidence_level IN ('높음', '중간', '낮음')),
    CONSTRAINT valid_direction CHECK (prediction_direction IN ('상승', '하락', '중립'))
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_backtest_ticker ON blog_backtest_results(ticker);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON blog_backtest_results(insight_date);
CREATE INDEX IF NOT EXISTS idx_backtest_success ON blog_backtest_results(success);
CREATE INDEX IF NOT EXISTS idx_backtest_confidence ON blog_backtest_results(confidence_level);

-- 2. 투자 시나리오 테이블
CREATE TABLE IF NOT EXISTS investment_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100) NOT NULL,
    scenario_type VARCHAR(20) NOT NULL,  -- "낙관적", "중립적", "비관적"
    probability FLOAT NOT NULL,  -- 0.0 ~ 1.0
    description TEXT,
    assumptions JSONB,  -- 핵심 가정 리스트
    asset_allocation JSONB,  -- 자산 배분 제안
    expected_return FLOAT,  -- 예상 수익률 (%)
    risk_level VARCHAR(20),  -- "낮음", "보통", "높음"
    success_probability FLOAT,  -- 성공 확률
    generated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT valid_probability CHECK (probability >= 0.0 AND probability <= 1.0),
    CONSTRAINT valid_scenario_type CHECK (scenario_type IN ('낙관적', '중립적', '비관적')),
    CONSTRAINT valid_risk_level CHECK (risk_level IN ('낮음', '보통', '높음'))
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_scenarios_active ON investment_scenarios(is_active);
CREATE INDEX IF NOT EXISTS idx_scenarios_generated ON investment_scenarios(generated_at);

-- 3. 사용자 포트폴리오 테이블
CREATE TABLE IF NOT EXISTS user_portfolios (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_date TIMESTAMP DEFAULT NOW(),
    total_value NUMERIC NOT NULL,
    holdings JSONB NOT NULL,  -- [{ticker, shares, avg_price, current_value}, ...]
    selected_scenario_id INTEGER REFERENCES investment_scenarios(id),
    cash_balance NUMERIC DEFAULT 0,
    risk_tolerance VARCHAR(20),  -- "낮음", "보통", "높음"

    CONSTRAINT valid_risk_tolerance CHECK (risk_tolerance IN ('낮음', '보통', '높음'))
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON user_portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_scenario ON user_portfolios(selected_scenario_id);

-- 4. 포트폴리오 거래 내역 테이블
CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    portfolio_id INTEGER REFERENCES user_portfolios(id),
    transaction_date TIMESTAMP DEFAULT NOW(),
    action VARCHAR(10) NOT NULL,  -- "BUY", "SELL"
    ticker VARCHAR(20) NOT NULL,
    shares NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    total_value NUMERIC NOT NULL,
    fee NUMERIC DEFAULT 0,
    reason TEXT,  -- "시나리오 1 선택으로 인한 리밸런싱"

    CONSTRAINT valid_action CHECK (action IN ('BUY', 'SELL')),
    CONSTRAINT positive_shares CHECK (shares > 0),
    CONSTRAINT positive_price CHECK (price > 0)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_transactions_user ON portfolio_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON portfolio_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON portfolio_transactions(ticker);

-- 5. 시나리오 성과 분석 테이블
CREATE TABLE IF NOT EXISTS scenario_performance (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES investment_scenarios(id),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    selection_date TIMESTAMP NOT NULL,
    evaluation_date TIMESTAMP,
    expected_return FLOAT,
    actual_return FLOAT,
    accuracy_score FLOAT,  -- 예측 정확도 (0-1)
    success BOOLEAN,
    max_drawdown FLOAT,  -- 최대 낙폭 (%)
    volatility FLOAT,  -- 변동성
    sharpe_ratio FLOAT,  -- 샤프 비율
    lessons_learned TEXT,  -- AI가 학습한 교훈

    CONSTRAINT valid_accuracy CHECK (accuracy_score >= 0.0 AND accuracy_score <= 1.0)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_performance_scenario ON scenario_performance(scenario_id);
CREATE INDEX IF NOT EXISTS idx_performance_user ON scenario_performance(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_success ON scenario_performance(success);

-- 6. AI 모델 가중치 테이블 (학습 데이터)
CREATE TABLE IF NOT EXISTS ai_model_weights (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50),  -- "블로그", "뉴스", "경제지표"
    weight FLOAT NOT NULL,
    confidence FLOAT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    update_reason TEXT,

    CONSTRAINT positive_weight CHECK (weight >= 0.0),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    UNIQUE(keyword, category)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_weights_keyword ON ai_model_weights(keyword);
CREATE INDEX IF NOT EXISTS idx_weights_category ON ai_model_weights(category);

-- 7. 자산 배분 제안 히스토리 테이블
CREATE TABLE IF NOT EXISTS asset_allocation_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES investment_scenarios(id),
    proposed_date TIMESTAMP DEFAULT NOW(),
    proposed_allocation JSONB NOT NULL,  -- 제안된 자산 배분
    current_allocation JSONB,  -- 현재 자산 배분
    rebalancing_plan JSONB,  -- 리밸런싱 계획
    implemented BOOLEAN DEFAULT FALSE,
    implementation_date TIMESTAMP,
    total_investment NUMERIC
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_allocation_user ON asset_allocation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_allocation_scenario ON asset_allocation_history(scenario_id);

-- 8. 시스템 학습 로그 테이블
CREATE TABLE IF NOT EXISTS system_learning_logs (
    id SERIAL PRIMARY KEY,
    log_date TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(50),  -- "백테스팅", "시나리오생성", "성과분석", "가중치조정"
    event_data JSONB,
    insights TEXT,  -- AI가 발견한 인사이트
    actions_taken TEXT,  -- 취한 조치
    impact_score FLOAT  -- 영향도 점수
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_learning_type ON system_learning_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_learning_date ON system_learning_logs(log_date);

-- 9. 시나리오별 키워드 매핑 테이블
CREATE TABLE IF NOT EXISTS scenario_keywords (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES investment_scenarios(id) ON DELETE CASCADE,
    keyword VARCHAR(100),
    relevance_score FLOAT,  -- 연관성 점수 (0-1)

    CONSTRAINT valid_relevance CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    UNIQUE(scenario_id, keyword)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_scenario_keyword ON scenario_keywords(keyword);

-- 10. 사용자 선호도 테이블
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    risk_tolerance VARCHAR(20),  -- "낮음", "보통", "높음"
    investment_goals TEXT,  -- 투자 목표
    preferred_asset_classes JSONB,  -- 선호 자산 분류
    excluded_tickers JSONB,  -- 제외할 종목
    rebalancing_frequency VARCHAR(20),  -- "매월", "분기", "반기", "연간"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_risk_pref CHECK (risk_tolerance IN ('낮음', '보통', '높음'))
);

-- Row Level Security (RLS) 설정
ALTER TABLE user_portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_allocation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- RLS 정책: 사용자는 자신의 데이터만 접근 가능
CREATE POLICY "Users can view their own portfolios"
    ON user_portfolios FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own portfolios"
    ON user_portfolios FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own portfolios"
    ON user_portfolios FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own transactions"
    ON portfolio_transactions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own transactions"
    ON portfolio_transactions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own performance"
    ON scenario_performance FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own allocation history"
    ON asset_allocation_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own preferences"
    ON user_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_preferences FOR UPDATE
    USING (auth.uid() = user_id);

-- 공개 읽기 정책: 시나리오는 모든 사용자가 볼 수 있음
CREATE POLICY "Anyone can view active scenarios"
    ON investment_scenarios FOR SELECT
    USING (is_active = TRUE);

CREATE POLICY "Anyone can view backtest results"
    ON blog_backtest_results FOR SELECT
    USING (TRUE);

-- 뷰 생성: 사용자별 성과 요약
CREATE OR REPLACE VIEW user_performance_summary AS
SELECT
    user_id,
    COUNT(DISTINCT scenario_id) as total_scenarios_used,
    AVG(actual_return) as avg_actual_return,
    AVG(accuracy_score) as avg_accuracy,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*)::FLOAT as success_rate,
    AVG(sharpe_ratio) as avg_sharpe_ratio
FROM scenario_performance
GROUP BY user_id;

-- 뷰: 시나리오별 성과 요약
CREATE OR REPLACE VIEW scenario_success_summary AS
SELECT
    s.id,
    s.scenario_name,
    s.scenario_type,
    COUNT(sp.id) as total_uses,
    AVG(sp.actual_return) as avg_actual_return,
    AVG(sp.accuracy_score) as avg_accuracy,
    SUM(CASE WHEN sp.success THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(sp.id), 0)::FLOAT as success_rate
FROM investment_scenarios s
LEFT JOIN scenario_performance sp ON s.id = sp.scenario_id
GROUP BY s.id, s.scenario_name, s.scenario_type;

-- 뷰: 블로그 백테스팅 통계
CREATE OR REPLACE VIEW backtest_statistics AS
SELECT
    prediction_topic,
    COUNT(*) as total_predictions,
    AVG(actual_return_pct) as avg_return,
    AVG(correlation_score) as avg_correlation,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*)::FLOAT as success_rate,
    confidence_level
FROM blog_backtest_results
GROUP BY prediction_topic, confidence_level
ORDER BY success_rate DESC;

-- 함수: 사용자 포트폴리오 스냅샷 생성
CREATE OR REPLACE FUNCTION create_portfolio_snapshot(
    p_user_id UUID,
    p_total_value NUMERIC,
    p_holdings JSONB,
    p_scenario_id INTEGER DEFAULT NULL,
    p_cash_balance NUMERIC DEFAULT 0
) RETURNS INTEGER AS $$
DECLARE
    v_portfolio_id INTEGER;
BEGIN
    INSERT INTO user_portfolios (user_id, total_value, holdings, selected_scenario_id, cash_balance)
    VALUES (p_user_id, p_total_value, p_holdings, p_scenario_id, p_cash_balance)
    RETURNING id INTO v_portfolio_id;

    RETURN v_portfolio_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 함수: AI 가중치 업데이트
CREATE OR REPLACE FUNCTION update_ai_weight(
    p_keyword VARCHAR(100),
    p_category VARCHAR(50),
    p_success BOOLEAN,
    p_impact FLOAT DEFAULT 0.1
) RETURNS VOID AS $$
DECLARE
    v_current_weight FLOAT;
    v_new_weight FLOAT;
BEGIN
    -- 현재 가중치 조회
    SELECT weight INTO v_current_weight
    FROM ai_model_weights
    WHERE keyword = p_keyword AND category = p_category;

    -- 가중치가 없으면 초기화
    IF v_current_weight IS NULL THEN
        v_current_weight := 0.5;
    END IF;

    -- 성공/실패에 따라 가중치 조정
    IF p_success THEN
        v_new_weight := LEAST(1.0, v_current_weight + p_impact);
    ELSE
        v_new_weight := GREATEST(0.0, v_current_weight - p_impact);
    END IF;

    -- 업데이트 또는 삽입
    INSERT INTO ai_model_weights (keyword, category, weight, confidence, success_count, failure_count, total_count)
    VALUES (
        p_keyword,
        p_category,
        v_new_weight,
        ABS(v_new_weight - 0.5) * 2,  -- confidence = 중심에서의 거리
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        1
    )
    ON CONFLICT (keyword, category) DO UPDATE SET
        weight = v_new_weight,
        confidence = ABS(v_new_weight - 0.5) * 2,
        success_count = ai_model_weights.success_count + CASE WHEN p_success THEN 1 ELSE 0 END,
        failure_count = ai_model_weights.failure_count + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_count = ai_model_weights.total_count + 1,
        last_updated = NOW(),
        update_reason = CASE
            WHEN p_success THEN '성공 사례로 가중치 증가'
            ELSE '실패 사례로 가중치 감소'
        END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 코멘트 추가
COMMENT ON TABLE blog_backtest_results IS '블로그 인사이트 백테스팅 결과';
COMMENT ON TABLE investment_scenarios IS 'AI 생성 투자 시나리오';
COMMENT ON TABLE user_portfolios IS '사용자 포트폴리오 스냅샷';
COMMENT ON TABLE portfolio_transactions IS '포트폴리오 거래 내역';
COMMENT ON TABLE scenario_performance IS '시나리오 성과 분석';
COMMENT ON TABLE ai_model_weights IS 'AI 모델 학습 가중치';
COMMENT ON TABLE asset_allocation_history IS '자산 배분 제안 히스토리';
COMMENT ON TABLE system_learning_logs IS '시스템 학습 로그';

-- 초기 데이터: AI 가중치 기본값
INSERT INTO ai_model_weights (keyword, category, weight, confidence) VALUES
('반도체', '블로그', 0.75, 0.5),
('AI', '블로그', 0.8, 0.6),
('금리', '경제지표', 0.7, 0.4),
('인플레이션', '경제지표', 0.65, 0.3),
('중국', '뉴스', 0.5, 0.0),
('미국', '뉴스', 0.55, 0.1)
ON CONFLICT (keyword, category) DO NOTHING;
