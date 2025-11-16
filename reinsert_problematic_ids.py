"""문제가 있는 ID들을 삭제하고 재삽입"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import time

def reinsert_problematic_ids():
    """ID 2116, 2120, 2121을 삭제하고 재삽입"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("문제 ID 재삽입 작업")
    print("=" * 80)

    problematic_ids = [2116, 2120, 2121]

    # 1. 백업
    print("\n1단계: 데이터 백업...")
    backups = {}

    for pid in problematic_ids:
        response = rag.client.table('investment_insights') \
            .select('*') \
            .eq('id', pid) \
            .execute()

        if response.data:
            backups[pid] = response.data[0]
            print(f"  ✅ ID {pid} 백업: {backups[pid]['title'][:50]}...")
        else:
            print(f"  ❌ ID {pid} 없음")

    if not backups:
        print("\n백업할 데이터가 없습니다.")
        return

    # 2. 삭제
    print(f"\n2단계: {len(backups)}개 글 삭제...")
    for pid in backups.keys():
        rag.client.table('investment_insights') \
            .delete() \
            .eq('id', pid) \
            .execute()
        print(f"  ✅ ID {pid} 삭제")

    # 3. 재삽입 (Supabase client 사용)
    print(f"\n3단계: {len(backups)}개 글 재삽입...")
    for pid, data in backups.items():
        # 임베딩 재생성
        text = f"{data['title']} {data['content']}"
        new_embedding = rag.generate_embedding(text)

        insert_data = {
            'id': pid,
            'title': data['title'],
            'content': data['content'],
            'sector': data['sector'],
            'sentiment': data['sentiment'],
            'keywords': data['keywords'],
            'url': data['url'],
            'date': data['date'],
            'embedding': new_embedding
        }

        rag.client.table('investment_insights') \
            .insert(insert_data) \
            .execute()

        print(f"  ✅ ID {pid} 삽입")

    # 4. 잠시 대기
    print("\n4단계: 인덱스 적용 대기 (3초)...")
    time.sleep(3)

    # 5. 검색 테스트
    print("\n5단계: 검색 테스트...")
    print("=" * 80)

    all_found = True

    for pid in backups.keys():
        response = rag.client.table('investment_insights') \
            .select('id, title') \
            .eq('id', pid) \
            .execute()

        if not response.data:
            print(f"ID {pid}: ❌ 재삽입 실패")
            all_found = False
            continue

        post = response.data[0]

        # 제목으로 검색
        results = rag.search_similar(post['title'], top_k=10)
        found = any(r['id'] == pid for r in results)

        status = "✅ 검색됨" if found else "❌ 검색 안 됨"
        print(f"ID {pid}: {status} - \"{post['title'][:50]}...\"")

        if found:
            for r in results:
                if r['id'] == pid:
                    print(f"  순위: {results.index(r) + 1}위, 유사도: {r['similarity']:.4f}")
        else:
            all_found = False

    print("\n" + "=" * 80)
    if all_found:
        print("✅ 모든 글 검색 성공!")
        print("   → 문제 해결 완료")
    else:
        print("❌ 일부 글 여전히 검색 안 됨")
        print("   → 추가 조치 필요")
    print("=" * 80)

if __name__ == '__main__':
    reinsert_problematic_ids()
