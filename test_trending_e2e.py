"""트렌딩 종목 E2E 테스트 스크립트"""
from playwright.sync_api import sync_playwright
import time


def test_trending_feature():
    """트렌딩 종목 E2E 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 콘솔 로그 캡처
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("\n" + "=" * 80)
        print("🔥 트렌딩 종목 E2E 테스트")
        print("=" * 80)

        # 1. 페이지 로드
        print("\n1️⃣ 페이지 로드...")
        page.goto('http://192.168.1.3:8888')
        page.wait_for_timeout(3000)
        print("✅ 페이지 로드 완료")

        # 2. AI 추천 확인
        print("\n2️⃣ AI 추천 종목 확인...")
        ai_items = page.locator('.stock-item').all()
        print(f"   AI 추천: {len(ai_items)}개 종목")

        # 3. 트렌딩 탭 클릭
        print("\n3️⃣ 트렌딩 탭 전환...")
        trending_tab = page.locator('button.tab:has-text("🔥 트렌딩")')

        if trending_tab.count() == 0:
            print("   ❌ 트렌딩 탭이 없습니다!")
            browser.close()
            return

        trending_tab.click()
        print("   ⏳ 트렌딩 종목 로딩 중 (15-20초 예상)...")
        page.wait_for_timeout(25000)  # 25초 대기

        # 4. 트렌딩 종목 확인
        trending_items = page.locator('.stock-item').all()
        print(f"\n   ✅ 트렌딩: {len(trending_items)}개 종목 로드됨")

        if len(trending_items) >= 5:
            print(f"   🎉 성공! {len(trending_items)}개 트렌딩 종목이 표시됨")
            print("\n   상위 5개 종목:")
            for i in range(min(5, len(trending_items))):
                symbol = trending_items[i].locator('.stock-symbol').text_content()
                name = trending_items[i].locator('.stock-name').text_content()
                price = trending_items[i].locator('.stock-price').text_content()
                change = trending_items[i].locator('.stock-change').text_content()
                print(f"     {i+1}. {symbol:<6} - {name:<30} : {price} ({change})")
        else:
            print(f"   ⚠️ 예상보다 적은 종목: {len(trending_items)}개")

        # 5. 첫 번째 트렌딩 종목 클릭
        if len(trending_items) > 0:
            print("\n4️⃣ 첫 번째 트렌딩 종목 상세 보기...")
            first_ticker = trending_items[0].locator('.stock-symbol').text_content()
            print(f"   종목: {first_ticker}")

            trending_items[0].click()
            page.wait_for_timeout(3000)  # 3초 대기

            # 종목명 확인
            stock_name = page.locator('#selectedStockName').text_content()
            stock_ticker = page.locator('#selectedStockTicker').text_content()
            current_price = page.locator('#currentPrice').text_content()

            print(f"   ✅ 상세 정보 로드 완료")
            print(f"      종목명: {stock_name}")
            print(f"      티커: {stock_ticker}")
            print(f"      현재가: {current_price}")

        # 6. 스크린샷
        print("\n5️⃣ 스크린샷 저장...")
        page.screenshot(path='trending_tab.png', full_page=True)
        print("✅ 스크린샷 저장: trending_tab.png")

        # 7. 콘솔 로그 출력
        print("\n6️⃣ 브라우저 콘솔 로그 (최근 30개):")
        for log in console_logs[-30:]:
            print(f"   {log}")

        browser.close()

        print("\n" + "=" * 80)
        print("🎉 E2E 테스트 완료!")
        print("=" * 80)
        print(f"\n📊 결과:")
        print(f"   - AI 추천: {len(ai_items)}개")
        print(f"   - 트렌딩: {len(trending_items)}개")
        print(f"\n💡 http://192.168.1.3:8888 에서 확인하세요!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    test_trending_feature()
