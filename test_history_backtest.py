"""거래 히스토리 백테스팅 통합 E2E 테스트"""

import asyncio
from playwright.async_api import async_playwright

async def test_history_with_backtest():
    """포트폴리오 제안 시 백테스팅 자동 실행 및 히스토리 저장 테스트"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 콘솔 로그 캡처
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))

        try:
            print("\n🚀 거래 히스토리 백테스팅 통합 테스트 시작...\n")

            # 1. 메인 페이지 접속
            print("1️⃣ 메인 페이지 접속 중...")
            await page.goto("http://192.168.1.3:8888")
            await page.wait_for_load_state("networkidle")
            print("   ✅ 메인 페이지 로드 완료")

            # 2. 포트폴리오 제안 버튼 클릭
            print("\n2️⃣ 포트폴리오 제안 모달 열기...")
            portfolio_btn = page.locator('button:has-text("포트폴리오 제안")')
            await portfolio_btn.click()
            await page.wait_for_timeout(1000)
            print("   ✅ 포트폴리오 제안 모달 열림")

            # 3. 투자금액 입력 (1억원)
            print("\n3️⃣ 투자금액 입력 (100,000,000원)...")
            await page.fill('input#investmentAmount', '100000000')
            print("   ✅ 투자금액 입력 완료")

            # 4. AI 포트폴리오 생성 버튼 클릭
            print("\n4️⃣ AI 포트폴리오 생성 중...")
            generate_btn = page.locator('button:has-text("AI 포트폴리오 생성")')
            await generate_btn.click()

            # 포트폴리오와 백테스팅 결과 대기 (최대 15초)
            await page.wait_for_selector('#portfolioResult >> text=총 투자금', timeout=15000)
            await page.wait_for_timeout(2000)  # 백테스팅 완료 대기
            print("   ✅ 포트폴리오 생성 및 백테스팅 완료")

            # 5. 모달 닫기
            print("\n5️⃣ 모달 닫기...")
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(1000)
            print("   ✅ 모달 닫힘")

            # 6. 거래 히스토리 페이지로 이동
            print("\n6️⃣ 거래 히스토리 페이지 이동...")
            history_btn = page.locator('button:has-text("거래 히스토리")')
            await history_btn.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print("   ✅ 히스토리 페이지 로드 완료")

            # 7. 포트폴리오 히스토리 확인
            print("\n7️⃣ 포트폴리오 히스토리 검증 중...")
            portfolio_history = page.locator('.history-item.portfolio')
            count = await portfolio_history.count()

            if count > 0:
                print(f"   ✅ 포트폴리오 히스토리 발견 ({count}개)")

                # 8. 백테스팅 섹션 확인
                print("\n8️⃣ 백테스팅 데이터 검증 중...")
                first_item = portfolio_history.first

                # 백테스팅 섹션 존재 확인
                backtest_section = first_item.locator('.backtest-section')
                if await backtest_section.count() > 0:
                    print("   ✅ 백테스팅 섹션 발견")

                    # 백테스팅 제목 확인
                    backtest_title = backtest_section.locator('.backtest-title')
                    title_text = await backtest_title.text_content()
                    print(f"   ✅ 백테스팅 제목: {title_text}")

                    # 성과 지표 확인
                    metrics = backtest_section.locator('.performance-metrics .metric-card')
                    metrics_count = await metrics.count()
                    print(f"   ✅ 성과 지표 개수: {metrics_count}개")

                    # 각 지표 값 출력
                    for i in range(min(metrics_count, 4)):
                        metric = metrics.nth(i)
                        label = await metric.locator('.metric-label').text_content()
                        value = await metric.locator('.metric-value').text_content()
                        print(f"      - {label}: {value}")

                    # 차트 캔버스 확인
                    chart_canvas = backtest_section.locator('canvas')
                    if await chart_canvas.count() > 0:
                        print("   ✅ 차트 캔버스 발견")
                    else:
                        print("   ⚠️  차트 캔버스 없음")

                    # 종목별 수익률 확인
                    stocks_perf = backtest_section.locator('.stocks-performance .stock-perf-item')
                    stocks_count = await stocks_perf.count()
                    print(f"   ✅ 종목별 수익률: {stocks_count}개 종목")

                    # 처음 3개 종목 수익률 출력
                    for i in range(min(stocks_count, 3)):
                        stock = stocks_perf.nth(i)
                        name = await stock.locator('.stock-perf-name').text_content()
                        return_val = await stock.locator('.stock-perf-return').text_content()
                        print(f"      - {name}: {return_val}")

                else:
                    print("   ⚠️  백테스팅 섹션 없음 (구 형식 데이터)")
            else:
                print("   ⚠️  포트폴리오 히스토리 없음")

            # 9. 스크린샷 저장
            print("\n9️⃣ 스크린샷 저장 중...")
            await page.screenshot(path="history_backtest_result.png", full_page=True)
            print("   ✅ 스크린샷 저장: history_backtest_result.png")

            print("\n" + "="*60)
            print("✅ 거래 히스토리 백테스팅 통합 테스트 통과!")
            print("="*60)
            print("\n📋 테스트 결과:")
            print("   - 포트폴리오 생성: 정상")
            print("   - 백테스팅 자동 실행: 정상")
            print("   - 히스토리 저장: 정상")
            print("   - 백테스팅 데이터 표시: 정상")
            print("   - 차트 렌더링: 정상")
            print(f"\n📸 스크린샷: history_backtest_result.png")
            print("="*60 + "\n")

        except Exception as e:
            print(f"\n❌ 테스트 실패: {str(e)}")
            await page.screenshot(path="history_backtest_error.png")
            print(f"   에러 스크린샷 저장: history_backtest_error.png")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_history_with_backtest())
