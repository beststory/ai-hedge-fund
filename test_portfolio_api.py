"""포트폴리오 및 백테스팅 API 직접 테스트"""

import requests
import json

BASE_URL = 'http://192.168.1.3:8888'

print("\n1️⃣ 포트폴리오 생성 API 테스트...")
portfolio_response = requests.post(
    f'{BASE_URL}/api/portfolio-suggestion',
    json={'total_investment': 100000000}
)

print(f"Status: {portfolio_response.status_code}")
portfolio_data = portfolio_response.json()
print(f"Success: {portfolio_data.get('success')}")

if portfolio_data.get('success'):
    print(f"Portfolio stocks: {len(portfolio_data.get('portfolio', []))}")
    print(f"Total investment: {portfolio_data.get('total_investment')}")

    print("\n2️⃣ 백테스팅 API 테스트...")
    backtest_response = requests.post(
        f'{BASE_URL}/api/portfolio-backtest',
        json={
            'portfolio': portfolio_data['portfolio'],
            'months_back': 3
        }
    )

    print(f"Status: {backtest_response.status_code}")
    print(f"Response: {json.dumps(backtest_response.json(), indent=2)}")
else:
    print(f"Error: {portfolio_data.get('message')}")
