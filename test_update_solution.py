"""UPDATE로 인덱스가 업데이트되는지 테스트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import time

def test_update_solution():
    """기존 ID를 UPDATE하면 검색이 되는지 테스트"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("UPDATE 방식 테스트")
    print("=" * 80)

    # 테스트용 기존 글 ID (가장 오래된 글 하나 선택)
    test_id = 1

    # 기존 내용 백업
    print(f"\n1. 기존 글 [ID: {test_id}] 백업...")
    backup = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', test_id) \
        .execute()

    if not backup.data:
        print("❌ 백업 실패")
        return

    original = backup.data[0]
    print(f"✅ 백업 완료: {original['title'][:50]}...")

    # 새 글 내용 가져오기
    print(f"\n2. 새 글 [ID: 2119] 내용 가져오기...")
    new_post = rag.client.table('investment_insights') \
        .select('*') \
        .eq('id', 2119) \
        .execute()

    if not new_post.data:
        print("❌ 새 글 없음")
        return

    new_content = new_post.data[0]
    print(f"✅ 새 글 내용: {new_content['title'][:50]}...")

    # UPDATE 실행
    print(f"\n3. 기존 ID {test_id}에 새 글 내용으로 UPDATE...")
    update_data = {
        'title': new_content['title'],
        'content': new_content['content'],
        'sector': new_content['sector'],
        'sentiment': new_content['sentiment'],
        'keywords': new_content['keywords'],
        'embedding': new_content['embedding'],
        'date': new_content['date'],
        'url': new_content['url']
    }

    result = rag.client.table('investment_insights') \
        .update(update_data) \
        .eq('id', test_id) \
        .execute()

    print(f"✅ UPDATE 완료")

    # 잠시 대기 (인덱스 업데이트 시간)
    print(f"\n4. 인덱스 업데이트 대기 중 (2초)...")
    time.sleep(2)

    # 검색 테스트 1: "토요일 새벽"
    print(f"\n5. 검색 테스트: '토요일 새벽'")
    results = rag.search_similar("토요일 새벽", top_k=10)

    found = any(r['id'] == test_id for r in results)
    print(f"검색 결과: {len(results)}개")
    print(f"ID {test_id} 발견: {'✅ Yes' if found else '❌ No'}")

    if found:
        for r in results:
            if r['id'] == test_id:
                print(f"  - 유사도: {r['similarity']:.4f}")
                print(f"  - 제목: {r['title'][:60]}...")

    # 검색 테스트 2: "암호화폐 청산"
    print(f"\n6. 검색 테스트: '암호화폐 청산'")
    results2 = rag.search_similar("암호화폐 청산", top_k=10)

    found2 = any(r['id'] == test_id for r in results2)
    print(f"검색 결과: {len(results2)}개")
    print(f"ID {test_id} 발견: {'✅ Yes' if found2 else '❌ No'}")

    if found2:
        for r in results2:
            if r['id'] == test_id:
                print(f"  - 유사도: {r['similarity']:.4f}")
                print(f"  - 제목: {r['title'][:60]}...")

    # 원래 내용으로 복원
    print(f"\n7. 원래 내용으로 복원...")
    restore_data = {
        'title': original['title'],
        'content': original['content'],
        'sector': original['sector'],
        'sentiment': original['sentiment'],
        'keywords': original['keywords'],
        'embedding': original['embedding'],
        'date': original['date'],
        'url': original['url']
    }

    rag.client.table('investment_insights') \
        .update(restore_data) \
        .eq('id', test_id) \
        .execute()

    print(f"✅ 복원 완료")

    print("\n" + "=" * 80)
    print("결론")
    print("=" * 80)

    if found or found2:
        print("✅ UPDATE 방식은 작동합니다!")
        print("   → 벡터 인덱스는 UPDATE 시 자동으로 업데이트됨")
        print("   → INSERT 시에만 인덱스가 업데이트 안 되는 문제")
        print("\n💡 해결책: INSERT 대신 UPSERT 사용하거나 인덱스 재구축 필요")
    else:
        print("❌ UPDATE도 작동하지 않습니다")
        print("   → 벡터 인덱스 자체에 문제가 있음")
        print("   → 인덱스 재구축이 반드시 필요")

if __name__ == '__main__':
    test_update_solution()
