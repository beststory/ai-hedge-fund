"""트렌딩 종목 분석기 테스트 스크립트"""
import sys
sys.path.insert(0, '/home/harvis/ai-hedge-fund')

from src.tools.trending_analyzer import get_trending_stocks, get_trending_analysis
import json


def test_trending_stocks():
    """트렌딩 종목 스크리닝 테스트"""
    print("\n" + "=" * 80)
    print("🔥 트렌딩 종목 스크리닝 테스트")
    print("=" * 80)

    print("\n1️⃣ 트렌딩 종목 수집 중 (15-20초 소요)...")
    trending_stocks = get_trending_stocks(min_score=40, top_n=10)

    print(f"\n✅ {len(trending_stocks)}개 트렌딩 종목 발견\n")

    if not trending_stocks:
        print("⚠️ 트렌딩 종목이 없습니다.")
        return

    # 테마별 분류
    themes = {}
    for stock in trending_stocks:
        theme = stock['theme']
        if theme not in themes:
            themes[theme] = []
        themes[theme].append(stock)

    print("📊 테마별 종목 분류:\n")
    for theme, stocks in themes.items():
        print(f"  🎯 {theme} ({len(stocks)}개)")
        for stock in stocks:
            print(f"     - {stock['ticker']:<6} | {stock['name']:<30} | "
                  f"가격: ${stock['current_price']:<8.2f} | "
                  f"1개월: {stock['returns_1m']:>6.1f}% | "
                  f"변동성: {stock['daily_volatility']:>5.1f}% | "
                  f"점수: {stock['trending_score']:.0f}")
        print()

    # 상위 3개 종목 상세 분석
    print("\n" + "=" * 80)
    print("📈 상위 3개 종목 상세 분석")
    print("=" * 80)

    for i, stock in enumerate(trending_stocks[:3], 1):
        ticker = stock['ticker']
        print(f"\n{i}️⃣ {ticker} ({stock['name']})")
        print(f"   테마: {stock['theme']}")
        print(f"   현재가: ${stock['current_price']}")
        print(f"   트렌딩 점수: {stock['trending_score']:.0f}/100")
        print(f"   리스크 레벨: {stock['risk_level']}")

        # 상세 분석
        print(f"\n   📊 상세 분석 가져오는 중...")
        analysis = get_trending_analysis(ticker)

        if analysis.get('success'):
            print(f"\n   💰 가격 변화:")
            for period, data in analysis['price_history'].items():
                if data:
                    print(f"      {period}: ${data['start']:.2f} → ${data['end']:.2f} "
                          f"({data['change']:+.1f}%)")

            print(f"\n   🎯 트렌딩 이유:")
            print(f"      {analysis['trending_reason']}")

            print(f"\n   ⚠️ 리스크 요소:")
            for risk in analysis['risk_factors']:
                print(f"      - {risk}")

            print(f"\n   📰 관련 뉴스 ({len(analysis['related_news'])}건):")
            for news in analysis['related_news'][:3]:
                print(f"      - {news['title']}")
                print(f"        ({news['source']}, {news['date']})")
        else:
            print(f"   ❌ 상세 분석 실패: {analysis.get('error', 'Unknown error')}")

        print("\n" + "-" * 80)

    print("\n" + "=" * 80)
    print("✅ 트렌딩 분석 테스트 완료!")
    print("=" * 80)

    # JSON 파일로 저장
    output_file = '/tmp/trending_stocks_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_count': len(trending_stocks),
            'stocks': trending_stocks,
            'themes': {theme: len(stocks) for theme, stocks in themes.items()}
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 결과 저장: {output_file}")


if __name__ == '__main__':
    test_trending_stocks()
