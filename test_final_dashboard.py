"""
최종 대시보드 테스트
- 왼쪽: AI 추천 종목 리스트 (10개)
- 가운데: 선택된 종목 상세 + 차트
- 오른쪽: AI 분석 + 뉴스
"""

from playwright.sync_api import sync_playwright
import time


def test_final_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "=" * 80)
        print("🎯 최종 대시보드 테스트")
        print("=" * 80)

        # 페이지 로드
        print("\n1️⃣ 페이지 로드...")
        page.goto('http://192.168.1.3:8888')
        page.wait_for_timeout(5000)
        print("✅ 페이지 로드 완료")

        # 왼쪽 종목 리스트 확인
        print("\n2️⃣ 왼쪽 사이드바 - 종목 리스트 확인...")
        page.wait_for_timeout(3000)
        stock_items = page.locator('.stock-item').all()
        print(f"   로드된 종목 수: {len(stock_items)}")

        if len(stock_items) > 0:
            for i, item in enumerate(stock_items[:5], 1):
                symbol = item.locator('.stock-symbol').text_content()
                price = item.locator('.stock-price').text_content()
                change = item.locator('.stock-change').text_content()
                print(f"   {i}. {symbol}: {price} ({change})")
            print("✅ 종목 리스트 정상 표시")
        else:
            print("❌ 종목 리스트가 비어있습니다!")

        # 중앙 종목 상세 확인
        print("\n3️⃣ 중앙 영역 - 선택된 종목 상세...")
        stock_name = page.locator('#selectedStockName').text_content()
        current_price = page.locator('#currentPrice').text_content()
        price_change = page.locator('#priceChange').text_content()

        print(f"   종목명: {stock_name}")
        print(f"   현재가: {current_price}")
        print(f"   변동: {price_change}")

        if current_price != "-":
            print("✅ 종목 상세 정보 정상 표시")
        else:
            print("❌ 종목 정보가 로드되지 않았습니다!")

        # 메타 정보 확인
        returns1m = page.locator('#returns1m').text_content()
        returns3m = page.locator('#returns3m').text_content()
        volatility = page.locator('#volatility').text_content()
        print(f"   1개월 수익률: {returns1m}")
        print(f"   3개월 수익률: {returns3m}")
        print(f"   변동성: {volatility}")

        # 차트 확인
        chart = page.locator('#priceChart')
        if chart.count() > 0:
            print("✅ 차트 표시됨")
        else:
            print("❌ 차트가 없습니다!")

        # 오른쪽 AI 분석 확인
        print("\n4️⃣ 오른쪽 사이드바 - AI 분석...")
        ai_recommendation = page.locator('#aiRecommendation').text_content()
        ai_analysis = page.locator('#aiAnalysis').text_content()

        print(f"   AI 추천: {ai_recommendation}")
        print(f"   분석 텍스트: {ai_analysis[:50]}...")

        if "분석 중" not in ai_recommendation:
            print("✅ AI 분석 정상 표시")
        else:
            print("⚠️ AI 분석이 아직 로딩 중입니다")

        # 뉴스 확인
        print("\n5️⃣ 오른쪽 사이드바 - 뉴스...")
        page.wait_for_timeout(2000)
        news_items = page.locator('.news-item').all()
        print(f"   로드된 뉴스 수: {len(news_items)}")

        if len(news_items) > 0:
            first_news = news_items[0].locator('.news-title').text_content()
            print(f"   첫 번째 뉴스: {first_news[:60]}...")
            print("✅ 뉴스 정상 표시")
        else:
            print("❌ 뉴스가 없습니다!")

        # 탭 전환 테스트
        print("\n6️⃣ 시장 탭 전환 테스트...")
        kospi_tab = page.locator('button.tab:has-text("KOSPI")')
        kospi_tab.click()
        print("   KOSPI 탭 클릭, 실시간 데이터 로딩 대기 중...")
        page.wait_for_timeout(8000)  # 실시간 API 호출 대기 (5개 종목 병렬 로드)

        stock_items_kospi = page.locator('.stock-item').all()
        print(f"   KOSPI 종목 수: {len(stock_items_kospi)}")

        if len(stock_items_kospi) > 0:
            first_kospi_symbol = stock_items_kospi[0].locator('.stock-symbol').text_content()
            first_kospi_price = stock_items_kospi[0].locator('.stock-price').text_content()
            print(f"   첫 번째 종목: {first_kospi_symbol} - {first_kospi_price}")
            print("✅ 시장 탭 전환 성공 (실시간 가격 로드됨)")
        else:
            print("❌ KOSPI 종목이 없습니다!")

        # 스크린샷
        print("\n7️⃣ 스크린샷 저장...")
        page.screenshot(path='final_dashboard.png', full_page=True)
        print("✅ 스크린샷 저장: final_dashboard.png")

        browser.close()

        print("\n" + "=" * 80)
        print("🎉 테스트 완료!")
        print("=" * 80)
        print("\n✨ 대시보드 구조:")
        print("   📊 왼쪽: AI 추천/KOSPI/NASDAQ 종목 리스트")
        print("   📈 가운데: 선택 종목 상세 + 차트 + 포트폴리오")
        print("   🤖 오른쪽: AI 분석 + 뉴스")
        print("\n💡 http://192.168.1.3:8888 에서 확인하세요!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    test_final_dashboard()
