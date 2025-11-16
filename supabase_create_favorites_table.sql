-- user_favorites 테이블 생성
CREATE TABLE IF NOT EXISTS public.user_favorites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id ON public.user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_symbol ON public.user_favorites(symbol);
CREATE INDEX IF NOT EXISTS idx_user_favorites_created_at ON public.user_favorites(created_at DESC);

-- RLS (Row Level Security) 활성화
ALTER TABLE public.user_favorites ENABLE ROW LEVEL SECURITY;

-- 정책: 사용자는 자신의 즐겨찾기만 조회 가능
CREATE POLICY "Users can view their own favorites"
ON public.user_favorites
FOR SELECT
USING (auth.uid() = user_id);

-- 정책: 사용자는 자신의 즐겨찾기만 추가 가능
CREATE POLICY "Users can insert their own favorites"
ON public.user_favorites
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- 정책: 사용자는 자신의 즐겨찾기만 삭제 가능
CREATE POLICY "Users can delete their own favorites"
ON public.user_favorites
FOR DELETE
USING (auth.uid() = user_id);

-- 코멘트 추가
COMMENT ON TABLE public.user_favorites IS '사용자별 즐겨찾기 종목';
COMMENT ON COLUMN public.user_favorites.user_id IS '사용자 ID (auth.users 참조)';
COMMENT ON COLUMN public.user_favorites.symbol IS '종목 심볼';
COMMENT ON COLUMN public.user_favorites.created_at IS '즐겨찾기 추가 시간';
