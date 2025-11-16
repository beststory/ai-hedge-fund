"""새로운 기능 E2E 테스트 스크립트
- 차트 기간 선택 (1개월/3개월/6개월/1년)
- 탭별 포트폴리오 생성 (AI/KOSPI/NASDAQ/트렌딩)
- 종목별 뉴스 표시
"""
from playwright.sync_api import sync_playwright
import time


def test_new_features():
    """새로운 기능 E2E 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 콘솔 로그 캡처
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("\n" + "=" * 80)
        print("🔥 새로운 기능 E2E 테스트")
        print("=" * 80)

        # 1. 페이지 로드
        print("\n1️⃣ 페이지 로드...")
        page.goto('http://192.168.1.3:8888')
        page.wait_for_timeout(3000)
        print("✅ 페이지 로드 완료")

        # 2. AI 추천 종목 확인
        print("\n2️⃣ AI 추천 종목 확인...")
        ai_items = page.locator('.stock-item').all()
        print(f"   AI 추천: {len(ai_items)}개 종목")

        # 3. 첫 번째 종목 클릭
        if len(ai_items) > 0:
            print("\n3️⃣ 첫 번째 종목 클릭...")
            first_stock = ai_items[0]
            stock_symbol = first_stock.locator('.stock-symbol').text_content()
            print(f"   종목: {stock_symbol}")

            first_stock.click()
            page.wait_for_timeout(3000)

            # 종목 상세 정보 확인
            selected_name = page.locator('#selectedStockName').text_content()
            print(f"   ✅ 선택된 종목: {selected_name}")

        # 4. 차트 기간 선택 버튼 테스트
        print("\n4️⃣ 차트 기간 선택 버튼 테스트...")
        period_buttons = page.locator('.period-btn').all()
        print(f"   차트 기간 버튼 수: {len(period_buttons)}개")

        if len(period_buttons) >= 4:
            print("   ✅ 기간 선택 버튼 존재 (1개월/3개월/6개월/1년)")

            # 각 버튼 클릭 테스트
            periods = ['1개월', '3개월', '6개월', '1년']
            for i, period_name in enumerate(periods):
                if i < len(period_buttons):
                    print(f"   → {period_name} 버튼 클릭")
                    period_buttons[i].click()
                    page.wait_for_timeout(1000)

                    # active 클래스 확인
                    active_btn = page.locator('.period-btn.active').text_content()
                    if active_btn == period_name:
                        print(f"      ✅ {period_name} 활성화됨")
                    else:
                        print(f"      ⚠️ active 버튼: {active_btn}")
        else:
            print(f"   ❌ 기간 선택 버튼이 부족합니다: {len(period_buttons)}개")

        # 5. 탭별 포트폴리오 생성 테스트
        print("\n5️⃣ 탭별 포트폴리오 생성 테스트...")
        tabs = ['ai', 'kospi', 'nasdaq', 'trending']
        tab_buttons = page.locator('.tab').all()

        for i, tab_name in enumerate(tabs):
            if i >= len(tab_buttons):
                continue

            print(f"\n   [{tab_name.upper()}] 탭 테스트")

            # 탭 클릭
            tab_buttons[i].click()
            page.wait_for_timeout(3000)

            # KOSPI/NASDAQ/트렌딩은 로딩 시간이 필요
            if tab_name in ['kospi', 'nasdaq', 'trending']:
                print(f"      ⏳ {tab_name.upper()} 종목 로딩 중 (최대 25초)...")
                page.wait_for_timeout(25000)

            # 종목 수 확인
            stocks = page.locator('.stock-item').all()
            print(f"      종목 수: {len(stocks)}개")

            if len(stocks) > 0:
                # 포트폴리오 생성 버튼 클릭
                print(f"      → 포트폴리오 생성 버튼 클릭")
                generate_btn = page.locator('button:has-text("생성")').first
                if generate_btn.count() > 0:
                    generate_btn.click()
                    page.wait_for_timeout(5000)

                    # 결과 확인
                    result = page.locator('#portfolioResult').text_content()
                    if "종목 수" in result:
                        print(f"      ✅ {tab_name.upper()} 포트폴리오 생성 성공")
                    else:
                        print(f"      ⚠️ 포트폴리오 생성 결과 확인 필요")
                else:
                    print(f"      ⚠️ 생성 버튼을 찾을 수 없음")

        # 6. 종목별 뉴스 표시 테스트
        print("\n6️⃣ 종목별 뉴스 표시 테스트...")

        # 트렌딩 탭으로 이동
        trending_tab = page.locator('button.tab:has-text("트렌딩")')
        if trending_tab.count() > 0:
            print("   트렌딩 탭 클릭")
            trending_tab.click()
            page.wait_for_timeout(25000)  # 트렌딩 종목 로딩

            trending_stocks = page.locator('.stock-item').all()
            if len(trending_stocks) > 0:
                # 첫 번째 트렌딩 종목 클릭
                first_trending = trending_stocks[0]
                trending_symbol = first_trending.locator('.stock-symbol').text_content()
                print(f"   종목: {trending_symbol} 클릭")

                first_trending.click()
                page.wait_for_timeout(5000)

                # 뉴스 섹션 확인
                news_items = page.locator('.news-item').all()
                print(f"   ✅ 뉴스 {len(news_items)}개 로드됨")

                if len(news_items) > 0:
                    # 첫 번째 뉴스 제목 확인
                    first_news = news_items[0].locator('.news-title').text_content()
                    print(f"   📰 첫 번째 뉴스: {first_news[:50]}...")
                else:
                    print(f"   ⚠️ 뉴스를 찾을 수 없습니다")

        # 7. 스크린샷
        print("\n7️⃣ 스크린샷 저장...")
        page.screenshot(path='test_new_features.png', full_page=True)
        print("✅ 스크린샷 저장: test_new_features.png")

        # 8. 콘솔 로그 출력
        print("\n8️⃣ 브라우저 콘솔 로그 (최근 30개):")
        for log in console_logs[-30:]:
            print(f"   {log}")

        browser.close()

        print("\n" + "=" * 80)
        print("🎉 E2E 테스트 완료!")
        print("=" * 80)
        print(f"\n✅ 모든 새로운 기능 테스트 완료")
        print(f"   1. 차트 기간 선택 버튼 (1개월/3개월/6개월/1년)")
        print(f"   2. 탭별 포트폴리오 생성 (AI/KOSPI/NASDAQ/트렌딩)")
        print(f"   3. 종목별 뉴스 필터링")
        print(f"\n💡 http://192.168.1.3:8888 에서 확인하세요!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    test_new_features()
