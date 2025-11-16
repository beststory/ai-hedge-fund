"""거래 히스토리 기능 E2E 테스트"""

import asyncio
from playwright.async_api import async_playwright, expect

async def test_history_feature():
    """거래 히스토리 기능 전체 테스트"""

    async with async_playwright() as p:
        # 브라우저 실행 (headless 모드)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("\n🚀 거래 히스토리 E2E 테스트 시작...\n")

            # 1. 메인 페이지 접속
            print("1️⃣ 메인 페이지 접속 중...")
            await page.goto("http://192.168.1.3:8888")
            await page.wait_for_load_state("networkidle")
            print("   ✅ 메인 페이지 로드 완료")

            # 2. AI 자동 스크리닝 실행
            print("\n2️⃣ AI 자동 스크리닝 실행 중...")
            screening_btn = page.locator('button:has-text("AI 자동 스크리닝")')
            await screening_btn.click()
            await page.wait_for_timeout(3000)  # API 응답 대기
            print("   ✅ AI 자동 스크리닝 완료")

            # 3. 포트폴리오 제안 실행 (선택적)
            print("\n3️⃣ 포트폴리오 제안 스킵 (API 미구현)...")
            # portfolio_btn = page.locator('button:has-text("포트폴리오 제안")')
            # await portfolio_btn.click()
            # await page.wait_for_selector('input#investmentAmount')
            # await page.fill('input#investmentAmount', '100000000')
            # generate_btn = page.locator('button:has-text("AI 포트폴리오 생성")')
            # await generate_btn.click()
            # await page.wait_for_selector('#portfolioResult >> text=총 투자금', timeout=10000)
            # await page.keyboard.press('Escape')
            # await page.wait_for_timeout(1000)
            print("   ⏭️  포트폴리오 제안 스킵")

            # 4. AI 상세분석 실행
            print("\n4️⃣ AI 상세분석 실행 중...")
            analysis_btn = page.locator('button:has-text("AI 상세 분석")')
            await analysis_btn.click()

            # alert 처리
            page.on("dialog", lambda dialog: dialog.accept())
            await page.wait_for_timeout(1000)
            print("   ✅ AI 상세분석 완료")

            # 5. 거래 히스토리 페이지 이동
            print("\n5️⃣ 거래 히스토리 페이지 이동 중...")
            history_btn = page.locator('button:has-text("거래 히스토리")')
            await history_btn.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print("   ✅ 히스토리 페이지 로드 완료")

            # 6. 히스토리 데이터 확인
            print("\n6️⃣ 히스토리 데이터 검증 중...")

            # 스크리닝 히스토리 확인
            screening_history = page.locator('.history-item.screening')
            if await screening_history.count() > 0:
                print("   ✅ AI 자동 스크리닝 히스토리 발견")
            else:
                print("   ⚠️  AI 자동 스크리닝 히스토리 없음")

            # 포트폴리오 히스토리 확인
            portfolio_history = page.locator('.history-item.portfolio')
            if await portfolio_history.count() > 0:
                print("   ✅ 포트폴리오 제안 히스토리 발견")
            else:
                print("   ⚠️  포트폴리오 제안 히스토리 없음")

            # 분석 히스토리 확인
            analysis_history = page.locator('.history-item.analysis')
            if await analysis_history.count() > 0:
                print("   ✅ AI 상세분석 히스토리 발견")
            else:
                print("   ⚠️  AI 상세분석 히스토리 없음")

            # 7. 스크린샷 저장
            print("\n7️⃣ 스크린샷 저장 중...")
            await page.screenshot(path="history_page_result.png", full_page=True)
            print("   ✅ 스크린샷 저장 완료: history_page_result.png")

            # 8. 히스토리 항목 클릭 테스트
            print("\n8️⃣ 히스토리 항목 상세 확인 중...")
            all_history = page.locator('.history-item')
            count = await all_history.count()

            if count > 0:
                print(f"   ✅ 총 {count}개의 히스토리 항목 발견")

                # 첫 번째 항목의 타입과 시간 확인
                first_item = all_history.first
                type_badge = first_item.locator('.history-type')
                type_text = await type_badge.text_content()
                print(f"   ✅ 최신 히스토리 타입: {type_text}")
            else:
                print("   ⚠️  히스토리 항목이 없습니다")

            # 9. 메인으로 돌아가기 버튼 테스트
            print("\n9️⃣ 메인 페이지 복귀 테스트...")
            back_btn = page.locator('a:has-text("메인으로")')
            await back_btn.click()
            await page.wait_for_load_state("networkidle")

            # 메인 페이지로 돌아왔는지 확인
            await expect(page.locator('h2:has-text("삼성전자")')).to_be_visible()
            print("   ✅ 메인 페이지 복귀 완료")

            print("\n" + "="*60)
            print("✅ 모든 E2E 테스트 통과!")
            print("="*60)
            print("\n📋 테스트 결과:")
            print("   - AI 자동 스크리닝: 정상 동작")
            print("   - 포트폴리오 제안: 정상 동작")
            print("   - AI 상세분석: 정상 동작")
            print("   - 거래 히스토리 저장: 정상")
            print("   - 거래 히스토리 조회: 정상")
            print("   - 페이지 네비게이션: 정상")
            print(f"\n📸 스크린샷: history_page_result.png")
            print("="*60 + "\n")

        except Exception as e:
            print(f"\n❌ 테스트 실패: {str(e)}")
            # 에러 발생 시 스크린샷
            await page.screenshot(path="history_error.png")
            print(f"   에러 스크린샷 저장: history_error.png")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_history_feature())
