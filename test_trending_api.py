"""트렌딩 종목 API 테스트 스크립트"""
import requests
import json


BASE_URL = "http://192.168.1.3:8888"


def test_trending_api():
    """트렌딩 종목 API 테스트"""
    print("\n" + "=" * 80)
    print("🔥 트렌딩 종목 API 테스트")
    print("=" * 80)

    # 1. 트렌딩 종목 리스트 조회
    print("\n1️⃣ GET /api/trending-stocks 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/api/trending-stocks?min_score=40&top_n=10")
        print(f"   상태 코드: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 성공!")
            print(f"   - 종목 수: {data['count']}")
            print(f"   - 테마: {list(data['themes'].keys())}")
            print(f"\n   상위 5개 종목:")
            for i, stock in enumerate(data['stocks'][:5], 1):
                print(f"      {i}. {stock['ticker']:<6} ({stock['name']:<30}) | "
                      f"점수: {stock['trending_score']:.0f} | 테마: {stock['theme']}")

            # 상세 분석 테스트를 위해 첫 번째 종목 저장
            first_ticker = data['stocks'][0]['ticker'] if data['stocks'] else None
        else:
            print(f"   ❌ 실패: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return

    # 2. 종목별 상세 분석
    if first_ticker:
        print(f"\n2️⃣ POST /api/trending-analysis 테스트 ({first_ticker})...")
        try:
            response = requests.post(
                f"{BASE_URL}/api/trending-analysis",
                json={"symbol": first_ticker}
            )
            print(f"   상태 코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 성공!")
                print(f"\n   📊 {data['name']} ({data['symbol']})")
                print(f"   - 현재가: ${data['current_price']}")
                print(f"   - 테마: {data['theme']}")

                print(f"\n   💰 가격 변화:")
                for period, price_data in data['price_history'].items():
                    if price_data:
                        print(f"      {period}: ${price_data['start']:.2f} → ${price_data['end']:.2f} "
                              f"({price_data['change']:+.1f}%)")

                print(f"\n   🎯 트렌딩 이유:")
                print(f"      {data['trending_reason']}")

                print(f"\n   ⚠️ 리스크 요소:")
                for risk in data['risk_factors']:
                    print(f"      - {risk}")

                print(f"\n   📰 관련 뉴스 ({len(data['related_news'])}건):")
                for news in data['related_news'][:3]:
                    print(f"      - {news['title']}")
            else:
                print(f"   ❌ 실패: {response.text}")
        except Exception as e:
            print(f"   ❌ 오류: {e}")

    print("\n" + "=" * 80)
    print("✅ API 테스트 완료!")
    print("=" * 80)
    print(f"\n💡 Swagger UI: {BASE_URL}/docs")


if __name__ == '__main__':
    test_trending_api()
