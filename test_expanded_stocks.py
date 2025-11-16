"""
확장된 종목 리스트 테스트 (KOSPI 30개, NASDAQ 25개)
"""

from playwright.sync_api import sync_playwright
import time


def test_expanded_stocks():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 콘솔 로그 캡처
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("\n" + "=" * 80)
        print("🎯 확장된 종목 리스트 테스트")
        print("=" * 80)

        # 페이지 로드
        print("\n1️⃣ 페이지 로드...")
        page.goto('http://192.168.1.3:8888')
        page.wait_for_timeout(5000)
        print("✅ 페이지 로드 완료")

        # AI 추천 종목 확인
        print("\n2️⃣ AI 추천 종목...")
        ai_items = page.locator('.stock-item').all()
        print(f"   AI 추천: {len(ai_items)}개 종목")

        # KOSPI 탭 클릭 및 대기
        print("\n3️⃣ KOSPI 탭 전환...")
        kospi_tab = page.locator('button.tab:has-text("KOSPI")')
        kospi_tab.click()
        print("   ⏳ KOSPI 30개 종목 로딩 중 (10-15초 예상)...")
        page.wait_for_timeout(20000)  # 20초 대기

        kospi_items = page.locator('.stock-item').all()
        print(f"   ✅ KOSPI: {len(kospi_items)}개 종목 로드됨")

        if len(kospi_items) >= 20:
            print(f"   🎉 성공! {len(kospi_items)}개 종목이 표시됨")
            # 처음 5개와 마지막 5개 종목 출력
            print("\n   처음 5개 종목:")
            for i in range(min(5, len(kospi_items))):
                symbol = kospi_items[i].locator('.stock-symbol').text_content()
                name = kospi_items[i].locator('.stock-name').text_content()
                price = kospi_items[i].locator('.stock-price').text_content()
                print(f"     {i+1}. {symbol} - {name} : {price}")

            if len(kospi_items) > 10:
                print(f"\n   마지막 5개 종목:")
                for i in range(max(0, len(kospi_items)-5), len(kospi_items)):
                    symbol = kospi_items[i].locator('.stock-symbol').text_content()
                    name = kospi_items[i].locator('.stock-name').text_content()
                    price = kospi_items[i].locator('.stock-price').text_content()
                    print(f"     {i+1}. {symbol} - {name} : {price}")
        else:
            print(f"   ⚠️ 예상보다 적은 종목: {len(kospi_items)}개")

        # NASDAQ 탭 클릭 및 대기
        print("\n4️⃣ NASDAQ 탭 전환...")
        nasdaq_tab = page.locator('button.tab:has-text("NASDAQ")')
        nasdaq_tab.click()
        print("   ⏳ NASDAQ 25개 종목 로딩 중 (최대 30초 대기)...")
        page.wait_for_timeout(30000)  # 30초 대기

        nasdaq_items = page.locator('.stock-item').all()
        print(f"   ✅ NASDAQ: {len(nasdaq_items)}개 종목 로드됨")

        if len(nasdaq_items) >= 20:
            print(f"   🎉 성공! {len(nasdaq_items)}개 종목이 표시됨")
            # 처음 5개 종목만 출력
            print("\n   처음 5개 종목:")
            for i in range(min(5, len(nasdaq_items))):
                symbol = nasdaq_items[i].locator('.stock-symbol').text_content()
                name = nasdaq_items[i].locator('.stock-name').text_content()
                price = nasdaq_items[i].locator('.stock-price').text_content()
                print(f"     {i+1}. {symbol} - {name} : {price}")
        else:
            print(f"   ⚠️ 예상보다 적은 종목: {len(nasdaq_items)}개")

        # 스크린샷
        print("\n5️⃣ 스크린샷 저장...")
        page.screenshot(path='expanded_stocks.png', full_page=True)
        print("✅ 스크린샷 저장: expanded_stocks.png")

        # 콘솔 로그 출력
        print("\n6️⃣ 브라우저 콘솔 로그:")
        for log in console_logs[-20:]:  # 마지막 20개만
            print(f"   {log}")

        browser.close()

        print("\n" + "=" * 80)
        print("🎉 테스트 완료!")
        print("=" * 80)
        print(f"\n📊 결과:")
        print(f"   - AI 추천: {len(ai_items)}개")
        print(f"   - KOSPI: {len(kospi_items)}개")
        print(f"   - NASDAQ: {len(nasdaq_items)}개")
        print(f"\n💡 http://192.168.1.3:8888 에서 스크롤하며 확인하세요!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    test_expanded_stocks()
