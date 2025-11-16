"""경제지표 및 뉴스 시스템 테스트"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.economic_indicators import (
    get_economic_indicators,
    get_market_condition
)
from src.tools.news_aggregator import (
    get_recent_news,
    analyze_news_sentiment
)


def test_us_indicators():
    """미국 경제지표 테스트"""
    print("\n" + "="*60)
    print("🇺🇸 미국 경제지표 테스트")
    print("="*60)
    
    indicators = get_economic_indicators("US")
    print(f"\n수집된 지표 수: {len(indicators)}")
    
    for ind in indicators:
        print(f"\n{ind.indicator_name}")
        print(f"  값: {ind.value} {ind.unit}")
        print(f"  날짜: {ind.date}")
        print(f"  설명: {ind.description}")


def test_korea_indicators():
    """한국 경제지표 테스트"""
    print("\n" + "="*60)
    print("🇰🇷 한국 경제지표 테스트")
    print("="*60)
    
    indicators = get_economic_indicators("KR")
    print(f"\n수집된 지표 수: {len(indicators)}")
    
    for ind in indicators:
        print(f"\n{ind.indicator_name}")
        print(f"  값: {ind.value} {ind.unit}")
        print(f"  날짜: {ind.date}")
        print(f"  설명: {ind.description}")


def test_market_condition():
    """시장 상황 분석 테스트"""
    print("\n" + "="*60)
    print("📊 시장 상황 분석 테스트")
    print("="*60)
    
    condition = get_market_condition()
    
    print(f"\n전체 전망: {condition.overall_sentiment.upper()}")
    print(f"리스크 레벨: {condition.risk_level.upper()}")
    print(f"\n분석 내용:")
    print(condition.analysis)
    print(f"\n분석 시각: {condition.timestamp}")


def test_news():
    """뉴스 수집 테스트"""
    print("\n" + "="*60)
    print("📰 뉴스 수집 테스트")
    print("="*60)
    
    news_list = get_recent_news(days=3, limit=10)
    print(f"\n수집된 뉴스: {len(news_list)}개")
    
    for i, news in enumerate(news_list[:5], 1):
        print(f"\n[{i}] {news.title}")
        print(f"    출처: {news.source} | 카테고리: {news.category}")
        print(f"    발행: {news.published_at}")
        if news.sentiment:
            print(f"    감성: {news.sentiment}")


def test_news_sentiment():
    """뉴스 감성 분석 테스트"""
    print("\n" + "="*60)
    print("💭 뉴스 감성 분석 테스트")
    print("="*60)
    
    news_list = get_recent_news(days=7, limit=30)
    sentiment = analyze_news_sentiment(news_list)
    
    print(f"\n전체 감성: {sentiment['overall'].upper()}")
    print(f"\n감성 분포:")
    print(f"  긍정: {sentiment['positive_ratio']}%")
    print(f"  부정: {sentiment['negative_ratio']}%")
    print(f"  중립: {sentiment['neutral_ratio']}%")
    
    print(f"\n개수:")
    print(f"  긍정: {sentiment['distribution']['positive']}개")
    print(f"  부정: {sentiment['distribution']['negative']}개")
    print(f"  중립: {sentiment['distribution']['neutral']}개")


def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 경제지표 및 뉴스 시스템 통합 테스트")
    print("="*60)
    
    try:
        # 미국 경제지표
        test_us_indicators()
        
        # 한국 경제지표
        test_korea_indicators()
        
        # 시장 상황 분석
        test_market_condition()
        
        # 뉴스 수집
        test_news()
        
        # 뉴스 감성 분석
        test_news_sentiment()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
        print("\n💡 팁:")
        print("- API 키를 설정하면 실시간 데이터를 사용할 수 있습니다")
        print("- .env 파일에 다음 키들을 추가하세요:")
        print("  * FRED_API_KEY (미국 경제지표)")
        print("  * ECOS_API_KEY (한국 경제지표)")
        print("  * NEWS_API_KEY (글로벌 뉴스)")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


