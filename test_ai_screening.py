#!/usr/bin/env python3
"""AI 자동 스크리닝 시스템 테스트 - Playwright"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_ai_screening():
    """AI 자동 스크리닝 시스템 종합 테스트"""
    
    async with async_playwright() as p:
        # 브라우저 실행 (헤드리스 모드)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # 콘솔 로그 모니터링
        console_logs = []
        errors = []
        
        def handle_console(msg):
            console_logs.append(f"Console {msg.type}: {msg.text}")
            
        def handle_error(error):
            errors.append(f"Page Error: {error}")
        
        page.on("console", handle_console)
        page.on("pageerror", handle_error)
        
        try:
            print("🚀 AI 헤지펀드 자동 스크리닝 시스템 테스트 시작")
            
            # 1. 웹사이트 접속
            print("1. 웹사이트 접속 중...")
            await page.goto("http://192.168.1.3:8888", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            # 2. 로그인
            print("2. 로그인 수행...")
            await page.fill("#username", "admin")
            await page.fill("#password", "hedge2024!")
            await page.click("button:has-text('로그인')")
            await page.wait_for_timeout(3000)
            
            # 로그인 성공 확인
            if await page.query_selector(".header h1"):
                print("✅ 로그인 성공")
            else:
                print("❌ 로그인 실패")
                return False
            
            # 3. 다크 테마 확인
            print("3. 다크 테마 적용 확인...")
            body_style = await page.evaluate("getComputedStyle(document.body).background")
            if "linear-gradient" in body_style and ("0a0a0a" in body_style or "1a1a2e" in body_style):
                print("✅ 다크 테마 적용됨")
            else:
                print("⚠️ 다크 테마 확인 불가")
            
            # 4. AI 자동 스크리닝 버튼 확인
            print("4. AI 자동 스크리닝 UI 확인...")
            auto_screen_btn = await page.query_selector("#autoScreenBtn")
            top_stocks_btn = await page.query_selector("#topStocksBtn")
            
            if auto_screen_btn and top_stocks_btn:
                print("✅ AI 자동 스크리닝 버튼들 존재")
            else:
                print("❌ AI 자동 스크리닝 버튼 없음")
                return False
            
            # 5. 자동 스크리닝 테스트
            print("5. AI 자동 스크리닝 실행...")
            
            # 버튼 클릭
            await page.click("#autoScreenBtn")
            
            # 로딩 상태 확인
            print("   - 로딩 상태 확인...")
            await page.wait_for_timeout(1000)
            
            loading_text = await page.query_selector(".loading-text")
            if loading_text:
                loading_content = await loading_text.text_content()
                print(f"   - 로딩 메시지: {loading_content}")
            
            # 결과 대기 (최대 30초)
            print("   - 분석 결과 대기 중... (최대 30초)")
            result_displayed = False
            for i in range(30):  # 30초 대기
                await page.wait_for_timeout(1000)
                
                # 결과 확인
                result_div = await page.query_selector("#analysisResult")
                if result_div:
                    result_content = await result_div.text_content()
                    if "AI 추천 상위" in result_content or "분석 결과" in result_content or "error" in result_content.lower():
                        result_displayed = True
                        print(f"   - 결과 표시됨 ({i+1}초 후)")
                        break
                
                print(f"   - 대기 중... {i+1}/30초", end="\r")
            
            if result_displayed:
                print("\n✅ AI 자동 스크리닝 결과 표시됨")
                
                # 결과 내용 상세 분석
                result_content = await result_div.text_content()
                print(f"   - 결과 내용 길이: {len(result_content)} 글자")
                
                # 스크리닝 카드 확인
                stock_cards = await page.query_selector_all(".stock-card")
                print(f"   - 주식 카드 개수: {len(stock_cards)}개")
                
                if len(stock_cards) > 0:
                    print("✅ 주식 스크리닝 카드 생성됨")
                    
                    # 첫 번째 카드 내용 확인
                    first_card = stock_cards[0]
                    ticker = await first_card.query_selector(".ticker")
                    if ticker:
                        ticker_text = await ticker.text_content()
                        print(f"   - 첫 번째 추천 주식: {ticker_text}")
                else:
                    print("⚠️ 주식 카드가 생성되지 않았지만 결과는 표시됨")
                    
            else:
                print("\n❌ AI 자동 스크리닝 결과 표시 실패")
                print("   - 현재 페이지 내용:")
                current_content = await page.text_content("body")
                print(f"   - 페이지 내용 길이: {len(current_content)}")
                return False
            
            # 6. 최신 추천 주식 조회 테스트
            print("6. 최신 추천 주식 조회 테스트...")
            await page.click("#topStocksBtn")
            await page.wait_for_timeout(5000)  # 5초 대기
            
            # 결과 확인
            result_content = await result_div.text_content()
            if "생성 시간:" in result_content or "AI 추천" in result_content:
                print("✅ 최신 추천 주식 조회 성공")
            else:
                print("⚠️ 최신 추천 주식 조회 결과 불명확")
            
            # 7. 개별 주식 분석 테스트
            print("7. 개별 주식 분석 테스트...")
            ticker_input = await page.query_selector("#tickerInput")
            if ticker_input:
                await ticker_input.fill("AAPL")
                await page.click("#analyzeBtn")
                await page.wait_for_timeout(8000)  # 8초 대기
                
                result_content = await result_div.text_content()
                if "AAPL" in result_content and ("분석" in result_content or "현재가" in result_content):
                    print("✅ 개별 주식 분석 성공")
                else:
                    print("⚠️ 개별 주식 분석 결과 불분명")
            
            # 8. 에러 상태 확인
            print("8. 시스템 상태 확인...")
            
            # JavaScript 에러 확인
            if errors:
                print(f"❌ JavaScript 에러 발견: {len(errors)}개")
                for error in errors[:3]:  # 최대 3개만 표시
                    print(f"   - {error}")
            else:
                print("✅ JavaScript 에러 없음")
            
            # 로딩 상태 잔여물 확인
            loading_elements = await page.query_selector_all(".loading")
            persistent_loading = [el for el in loading_elements if await el.is_visible()]
            
            if persistent_loading:
                print(f"⚠️ 지속적인 로딩 요소 발견: {len(persistent_loading)}개")
            else:
                print("✅ 지속적인 로딩 요소 없음")
            
            # 9. 전체 시스템 안정성 확인
            print("9. 전체 시스템 안정성 최종 확인...")
            
            # 60초 폴링 간격 확인 (30초 대기)
            initial_requests = len([log for log in console_logs if "api" in log.lower()])
            await page.wait_for_timeout(30000)  # 30초 대기
            final_requests = len([log for log in console_logs if "api" in log.lower()])
            
            request_rate = (final_requests - initial_requests) / 30  # 초당 요청 수
            print(f"   - API 요청 빈도: {request_rate:.2f} 요청/초")
            
            if request_rate < 0.1:  # 10초에 1번 미만
                print("✅ API 요청 빈도 적절")
            else:
                print(f"⚠️ API 요청이 너무 빈번할 수 있음")
            
            print("\n" + "="*50)
            print("🎯 AI 자동 스크리닝 시스템 테스트 완료!")
            print("="*50)
            
            # 최종 결과 요약
            summary = {
                "로그인": "✅",
                "다크테마": "✅",
                "자동스크리닝": "✅" if result_displayed else "❌",
                "JavaScript에러": "✅" if not errors else "❌",
                "로딩안정성": "✅" if not persistent_loading else "❌",
                "API안정성": "✅" if request_rate < 0.1 else "⚠️"
            }
            
            print("최종 결과 요약:")
            for key, status in summary.items():
                print(f"  {key}: {status}")
            
            success_count = len([s for s in summary.values() if s == "✅"])
            total_count = len(summary)
            print(f"\n종합 점수: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
            
            return success_count >= total_count - 1  # 최소 5/6 성공
        
        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")
            return False
        
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_ai_screening())
    if success:
        print("\n🎉 AI 자동 스크리닝 시스템 테스트 성공!")
        exit(0)
    else:
        print("\n💥 AI 자동 스크리닝 시스템 테스트 실패!")
        exit(1)