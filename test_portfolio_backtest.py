"""
Playwright E2E 테스트 - 포트폴리오 제안 및 백테스팅 기능
"""

import asyncio
from playwright.async_api import async_playwright, expect
import time


async def main():
    print("🚀 AI 헤지펀드 포트폴리오 백테스팅 E2E 테스트 시작...")

    async with async_playwright() as p:
        # 브라우저 실행 (headless 모드)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            # 1. 웹사이트 접속
            print("\n📍 단계 1: 웹사이트 접속 (http://192.168.1.3:8888)")
            await page.goto("http://192.168.1.3:8888", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # 2. 포트폴리오 제안 버튼 클릭
            print("\n💼 단계 2: 포트폴리오 제안 버튼 클릭")
            await page.click('button:has-text("포트폴리오 제안")')
            await page.wait_for_timeout(1000)

            # 3. 투자 금액 확인 (기본값: 1억원)
            print("\n💰 단계 3: 투자 금액 확인")
            investment_input = await page.locator('#investmentAmount').input_value()
            print(f"   ✅ 투자 금액: {int(investment_input):,}원")

            # 4. AI 포트폴리오 생성 버튼 클릭
            print("\n🤖 단계 4: AI 포트폴리오 생성 버튼 클릭")
            await page.click('button:has-text("AI 포트폴리오 생성")')

            # 5. 포트폴리오 결과 대기
            print("\n⏳ 단계 5: AI 포트폴리오 생성 대기 중...")
            await page.wait_for_selector('#portfolioResult >> text=총 투자금', timeout=60000)
            await page.wait_for_timeout(2000)

            # 6. 포트폴리오 요약 정보 확인
            print("\n📊 단계 6: 포트폴리오 요약 정보 확인")
            summary_text = await page.locator('#portfolioResult').inner_text()
            if "총 투자금" in summary_text and "예상 수익률" in summary_text:
                print("   ✅ 포트폴리오 요약 정보 표시됨")

            # 7. 백테스팅 버튼 클릭
            print("\n📈 단계 7: 과거 3개월 수익률 보기 버튼 클릭")
            await page.click('button:has-text("과거 3개월 수익률 보기")')
            await page.wait_for_timeout(1000)

            # 8. 백테스팅 결과 대기
            print("\n⏳ 단계 8: 백테스팅 결과 대기 중...")
            await page.wait_for_selector('canvas#backtestChart', timeout=60000)
            await page.wait_for_timeout(3000)

            # 9. 백테스팅 결과 확인
            print("\n📈 단계 9: 백테스팅 결과 확인")
            backtest_modal = await page.locator('#backtestResult').inner_text()

            # 필수 요소 체크
            checks = {
                "총 수익률": "총 수익률" in backtest_modal,
                "초기 투자금": "초기 투자금" in backtest_modal,
                "최종 가치": "최종 가치" in backtest_modal,
                "변동성": "변동성" in backtest_modal,
                "최대 낙폭": "최대 낙폭" in backtest_modal,
                "샤프 비율": "샤프 비율" in backtest_modal,
                "종목별 수익률": "종목별 수익률" in backtest_modal,
            }

            print("\n   📋 백테스팅 결과 요소 확인:")
            for item, found in checks.items():
                status = "✅" if found else "❌"
                print(f"      {status} {item}: {'표시됨' if found else '미표시'}")

            # 11. 차트 캔버스 존재 확인
            chart_exists = await page.locator('canvas#backtestChart').is_visible()
            print(f"\n   📊 수익률 차트: {'✅ 표시됨' if chart_exists else '❌ 미표시'}")

            # 10. 스크린샷 저장
            print("\n📸 단계 10: 백테스팅 결과 스크린샷 저장")
            await page.screenshot(path='backtest_result.png', full_page=True)
            print("   ✅ 스크린샷 저장: backtest_result.png")

            # 11. 최종 확인
            print("\n" + "="*60)
            all_passed = all(checks.values()) and chart_exists
            if all_passed:
                print("✅ 모든 E2E 테스트 통과!")
                print("   - 포트폴리오 제안 기능: 정상")
                print("   - 백테스팅 기능: 정상")
                print("   - 수익률 차트: 정상")
            else:
                print("❌ 일부 테스트 실패")
            print("="*60)

            # 결과 보기 위해 5초 대기
            print("\n⏳ 5초 후 브라우저 종료...")
            await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
            await page.screenshot(path='error_screenshot.png')
            print("   📸 오류 스크린샷 저장: error_screenshot.png")

        finally:
            await browser.close()
            print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
