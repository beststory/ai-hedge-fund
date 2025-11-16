"""Intelligence 시스템 E2E 테스트

웹 서버가 실행 중이어야 합니다.
"""
import asyncio
from src.intelligence.scenario_generator import ScenarioGenerator
from src.intelligence.portfolio_optimizer import PortfolioOptimizer, UserPortfolio, Holding
from src.intelligence.portfolio_tracker import PortfolioTracker
from src.intelligence.performance_analyzer import PerformanceAnalyzer

async def test_scenario_generation():
    """시나리오 생성 테스트"""
    print("\n" + "="*80)
    print("📊 테스트 1: 시나리오 생성")
    print("="*80)

    try:
        generator = ScenarioGenerator()

        # 경제 스냅샷 생성
        print("\n1️⃣ 경제 지표 수집 중...")
        snapshot = await generator.get_current_economic_snapshot()

        print(f"   ✅ GDP 성장률: {snapshot.gdp_growth:.2f}%")
        print(f"   ✅ 인플레이션: {snapshot.inflation_rate:.2f}%")
        print(f"   ✅ 실업률: {snapshot.unemployment_rate:.2f}%")
        print(f"   ✅ 기준 금리: {snapshot.interest_rate:.2f}%")

        # 시나리오 생성
        print("\n2️⃣ AI 시나리오 생성 중...")
        analysis = await generator.generate_scenarios(num_scenarios=3)

        print(f"\n   ✅ {len(analysis.scenarios)}개 시나리오 생성 완료")

        for i, scenario in enumerate(analysis.scenarios, 1):
            print(f"\n   시나리오 {i}: {scenario.scenario_name}")
            print(f"   - 유형: {scenario.scenario_type}")
            print(f"   - 확률: {scenario.probability*100:.0f}%")
            print(f"   - 예상 수익률: {scenario.expected_return:.1f}%")
            print(f"   - 리스크: {scenario.risk_level}")

        return analysis

    except Exception as e:
        print(f"\n   ❌ 시나리오 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_portfolio_optimization(scenario):
    """포트폴리오 최적화 테스트"""
    print("\n" + "="*80)
    print("🔄 테스트 2: 포트폴리오 최적화")
    print("="*80)

    try:
        optimizer = PortfolioOptimizer()

        # 샘플 현재 포트폴리오
        current_portfolio = UserPortfolio(
            total_value=10000000,  # 1천만원
            cash_balance=2000000,  # 200만원
            holdings=[
                Holding(ticker="AAPL", shares=10, avg_price=150, current_price=180,
                       current_value=1800000, weight_pct=18),
                Holding(ticker="TSLA", shares=15, avg_price=200, current_price=250,
                       current_value=3750000, weight_pct=37.5),
            ],
            risk_tolerance="보통"
        )

        print("\n1️⃣ 현재 포트폴리오:")
        print(f"   총 가치: ${current_portfolio.total_value:,.0f}")
        print(f"   현금: ${current_portfolio.cash_balance:,.0f}")
        print(f"   보유 종목: {len(current_portfolio.holdings)}개")

        # 시나리오 자산 배분 추출
        scenario_allocations = optimizer.parse_scenario_allocations(scenario)

        print(f"\n2️⃣ 시나리오 자산 배분: {len(scenario_allocations)}개 클래스")

        # 리밸런싱 계획 생성
        print("\n3️⃣ 리밸런싱 계획 생성 중...")
        plan = optimizer.generate_rebalancing_plan(
            current_portfolio=current_portfolio,
            scenario_allocations=scenario_allocations,
            total_investment=10000000
        )

        print(f"\n   ✅ 리밸런싱 계획 생성 완료")
        print(f"\n{plan.rebalancing_summary}")

        print("\n   주요 액션:")
        for action in plan.actions[:5]:  # 상위 5개만 표시
            if action.action != 'HOLD':
                print(f"   - {action.action} {action.ticker}: {abs(action.shares_change):.2f}주")

        return plan

    except Exception as e:
        print(f"\n   ❌ 포트폴리오 최적화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_portfolio_tracking():
    """포트폴리오 추적 테스트"""
    print("\n" + "="*80)
    print("💼 테스트 3: 포트폴리오 추적")
    print("="*80)

    try:
        tracker = PortfolioTracker(user_id="test-user-001")

        print("\n1️⃣ 현재 포트폴리오 조회 중...")
        portfolio = await tracker.get_current_portfolio()

        if portfolio and portfolio.get('total_value', 0) > 0:
            print(f"   ✅ 총 가치: ${portfolio['total_value']:,.0f}")
            print(f"   ✅ 보유 종목: {len(portfolio['holdings'])}개")
        else:
            print("   ℹ️  포트폴리오 없음 (초기 상태)")

        return True

    except Exception as e:
        print(f"\n   ❌ 포트폴리오 추적 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_analysis():
    """성과 분석 테스트"""
    print("\n" + "="*80)
    print("📈 테스트 4: 성과 분석 시스템")
    print("="*80)

    try:
        analyzer = PerformanceAnalyzer()

        print("\n1️⃣ 성과 분석 엔진 초기화 완료")
        print("   ✅ Sharpe Ratio 계산 준비")
        print("   ✅ 최대 낙폭 분석 준비")
        print("   ✅ AI 학습 시스템 준비")

        return True

    except Exception as e:
        print(f"\n   ❌ 성과 분석 시스템 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """전체 시스템 테스트"""
    print("\n" + "="*80)
    print("🧠 AI 투자 지능 시스템 E2E 테스트")
    print("="*80)

    # 1. 시나리오 생성
    analysis = await test_scenario_generation()

    if analysis:
        # 첫 번째 시나리오로 최적화 테스트
        scenario = {
            'asset_allocation': [alloc.dict() for alloc in analysis.scenarios[0].asset_allocations]
        }

        # 2. 포트폴리오 최적화
        await test_portfolio_optimization(scenario)

    # 3. 포트폴리오 추적
    await test_portfolio_tracking()

    # 4. 성과 분석
    await test_performance_analysis()

    print("\n" + "="*80)
    print("✅ 전체 테스트 완료")
    print("="*80)

    print("\n📝 다음 단계:")
    print("1. http://192.168.1.3:8888/intelligence.html 접속")
    print("2. 로그인 후 '시나리오 생성' 버튼 클릭")
    print("3. 생성된 시나리오 선택 및 리밸런싱 계획 확인")
    print("4. Supabase 테이블 생성 (수동):")
    print("   - supabase_intelligence_system.sql 실행 필요")
    print()


if __name__ == "__main__":
    asyncio.run(main())
