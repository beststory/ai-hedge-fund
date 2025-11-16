"""임베딩 저장 형식 확인 스크립트"""
import sys
sys.path.append('/home/harvis/ai-hedge-fund')

from src.tools.supabase_rag import SupabaseRAG
import json

def check_embedding_format():
    """임베딩 저장 형식 상세 분석"""
    rag = SupabaseRAG()

    print("=" * 80)
    print("임베딩 저장 형식 분석")
    print("=" * 80)

    # 기존 글 하나 (잘 검색되는 글)
    old_post = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .eq('id', 1928) \
        .execute()

    # 새 글 (검색 안 되는 글)
    new_post = rag.client.table('investment_insights') \
        .select('id, title, embedding') \
        .eq('id', 2119) \
        .execute()

    if old_post.data:
        old = old_post.data[0]
        print(f"\n✅ 기존 글 [ID: {old['id']}] - 검색 잘 됨")
        print(f"제목: {old['title'][:60]}...")

        old_emb = old['embedding']
        print(f"임베딩 Python 타입: {type(old_emb).__name__}")

        if isinstance(old_emb, str):
            print(f"임베딩 문자열 길이: {len(old_emb)}")
            print(f"임베딩 시작 100자: {old_emb[:100]}")

            # JSON 파싱 시도
            try:
                parsed = json.loads(old_emb)
                print(f"JSON 파싱: ✅ 성공")
                print(f"파싱 후 타입: {type(parsed).__name__}")
                if isinstance(parsed, list):
                    print(f"배열 길이: {len(parsed)}")
                    print(f"첫 5개 값: {parsed[:5]}")
            except:
                print(f"JSON 파싱: ❌ 실패")
        elif isinstance(old_emb, list):
            print(f"임베딩 배열 길이: {len(old_emb)}")
            print(f"첫 5개 값: {old_emb[:5]}")

    if new_post.data:
        new = new_post.data[0]
        print(f"\n❌ 새 글 [ID: {new['id']}] - 검색 안 됨")
        print(f"제목: {new['title'][:60]}...")

        new_emb = new['embedding']
        print(f"임베딩 Python 타입: {type(new_emb).__name__}")

        if isinstance(new_emb, str):
            print(f"임베딩 문자열 길이: {len(new_emb)}")
            print(f"임베딩 시작 100자: {new_emb[:100]}")

            # JSON 파싱 시도
            try:
                parsed = json.loads(new_emb)
                print(f"JSON 파싱: ✅ 성공")
                print(f"파싱 후 타입: {type(parsed).__name__}")
                if isinstance(parsed, list):
                    print(f"배열 길이: {len(parsed)}")
                    print(f"첫 5개 값: {parsed[:5]}")
            except:
                print(f"JSON 파싱: ❌실패")
        elif isinstance(new_emb, list):
            print(f"임베딩 배열 길이: {len(new_emb)}")
            print(f"첫 5개 값: {new_emb[:5]}")

    # 형식 비교
    if old_post.data and new_post.data:
        old_emb = old_post.data[0]['embedding']
        new_emb = new_post.data[0]['embedding']

        print("\n" + "=" * 80)
        print("비교 결과")
        print("=" * 80)

        print(f"타입 동일: {type(old_emb) == type(new_emb)}")
        print(f"기존 글 타입: {type(old_emb).__name__}")
        print(f"새 글 타입: {type(new_emb).__name__}")

        # 문자열 형식 비교
        if isinstance(old_emb, str) and isinstance(new_emb, str):
            print(f"\n문자열 길이 비슷: {abs(len(old_emb) - len(new_emb)) < 100}")
            print(f"기존 글 길이: {len(old_emb)}")
            print(f"새 글 길이: {len(new_emb)}")

            # 시작 부분 비교
            old_start = old_emb[:50]
            new_start = new_emb[:50]
            print(f"\n시작 형식 비교:")
            print(f"기존: {old_start}")
            print(f"새글: {new_start}")

    print("\n" + "=" * 80)
    print("임베딩 직접 생성 테스트")
    print("=" * 80)

    # 새로운 임베딩 생성
    test_text = "테스트 텍스트"
    test_embedding = rag.generate_embedding(test_text)

    print(f"\n생성된 임베딩 타입: {type(test_embedding).__name__}")
    print(f"임베딩 길이: {len(test_embedding)}")
    print(f"첫 5개 값: {test_embedding[:5]}")

    # 이 임베딩을 저장할 때 어떻게 변환되는지 확인
    print(f"\nJSON 직렬화 테스트:")
    json_str = json.dumps(test_embedding)
    print(f"JSON 문자열 길이: {len(json_str)}")
    print(f"JSON 문자열 시작: {json_str[:100]}")

if __name__ == '__main__':
    check_embedding_format()
