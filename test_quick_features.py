"""빠른 기능 테스트 - 핵심 기능만"""
from playwright.sync_api import sync_playwright
import time


def test_quick_features():
    """빠른 핵심 기능 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "=" * 80)
        print("⚡ 빠른 기능 테스트")
        print("=" * 80)

        # 1. 페이지 로드
        print("\n1️⃣ 페이지 로드...")
        page.goto('http://192.168.1.3:8888')
        page.wait_for_timeout(3000)
        print("✅ 페이지 로드 완료")

        # 2. AI 추천 종목 확인
        print("\n2️⃣ AI 추천 종목 확인...")
        ai_items = page.locator('.stock-item').all()
        print(f"   ✅ AI 추천: {len(ai_items)}개 종목")

        # 3. 차트 기간 선택 버튼 확인
        print("\n3️⃣ 차트 기간 선택 버튼 확인...")
        period_buttons = page.locator('.period-btn').all()
        print(f"   버튼 수: {len(period_buttons)}개")

        if len(period_buttons) >= 4:
            print("   ✅ 기간 선택 버튼 존재 (4개)")

            # 1년 버튼 클릭
            print("   → 1년 버튼 클릭")
            page.locator('button.period-btn:has-text("1년")').click()
            page.wait_for_timeout(1000)

            active_btn = page.locator('.period-btn.active').text_content()
            print(f"   ✅ Active: {active_btn}")
        else:
            print(f"   ❌ 버튼 부족: {len(period_buttons)}개")

        # 4. AI 탭에서 포트폴리오 생성
        print("\n4️⃣ AI 탭 포트폴리오 생성...")
        generate_btn = page.locator('button:has-text("생성")').first
        if generate_btn.count() > 0:
            print("   생성 버튼 클릭")
            generate_btn.click()
            page.wait_for_timeout(5000)

            result = page.locator('#portfolioResult').text_content()
            if "종목 수" in result or "생성 중" in result:
                print("   ✅ 포트폴리오 생성 성공 또는 진행 중")
            else:
                print(f"   ⚠️ 결과: {result[:100]}")

        # 5. 첫 번째 종목 클릭하여 뉴스 확인
        print("\n5️⃣ 종목 클릭 후 뉴스 확인...")
        if len(ai_items) > 0:
            first_stock = ai_items[0]
            stock_symbol = first_stock.locator('.stock-symbol').text_content()
            print(f"   종목: {stock_symbol} 클릭")

            first_stock.click()
            page.wait_for_timeout(5000)

            # 뉴스 확인
            news_items = page.locator('.news-item').all()
            print(f"   ✅ 뉴스: {len(news_items)}개")

            if len(news_items) > 0:
                first_news = news_items[0].locator('.news-title').text_content()
                print(f"   📰 {first_news[:60]}...")

        # 6. 스크린샷
        print("\n6️⃣ 스크린샷 저장...")
        page.screenshot(path='test_quick.png', full_page=True)
        print("✅ 스크린샷: test_quick.png")

        browser.close()

        print("\n" + "=" * 80)
        print("✅ 테스트 완료!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    test_quick_features()
