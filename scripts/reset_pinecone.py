#!/usr/bin/env python3
"""
Pinecone 인덱스 초기화 스크립트
임베딩 차원 변경 시 기존 인덱스를 삭제하고 새로 생성합니다.
"""

import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# 환경 변수 로드
load_dotenv()

def reset_pinecone_index():
    """Pinecone 인덱스를 초기화합니다."""
    
    # API 키 확인
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY가 설정되지 않았습니다.")
        return False
    
    # Pinecone 클라이언트 초기화
    pc = Pinecone(api_key=api_key)
    
    # 인덱스 정보
    index_name = os.getenv("PINECONE_INDEX_NAME", "lamy-memories")
    region = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    
    print(f"🔍 인덱스 확인: {index_name}")
    
    # 기존 인덱스 목록 확인
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    print(f"📋 기존 인덱스 목록: {existing_indexes}")
    
    # 기존 인덱스 삭제
    if index_name in existing_indexes:
        print(f"🗑️  기존 인덱스 삭제 중: {index_name}")
        pc.delete_index(index_name)
        
        # 삭제 완료 대기
        print("⏳ 인덱스 삭제 대기 중...")
        while index_name in [idx["name"] for idx in pc.list_indexes()]:
            time.sleep(2)
            print(".", end="", flush=True)
        print("\n✅ 인덱스 삭제 완료!")
    
    # 새 인덱스 생성
    print(f"🆕 새 인덱스 생성 중: {index_name} (1536차원)")
    pc.create_index(
        name=index_name,
        dimension=1536,  # OpenAI text-embedding-3-small
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region=region
        )
    )
    
    # 인덱스 준비 대기
    print("⏳ 인덱스 준비 대기 중...")
    max_retries = 30
    for i in range(max_retries):
        try:
            index_info = pc.describe_index(index_name)
            if index_info.status.ready:
                print(f"\n✅ 인덱스 준비 완료: {index_name}")
                print(f"📊 차원: {index_info.dimension}")
                print(f"📍 지역: {index_info.spec.serverless.region}")
                return True
        except Exception as e:
            print(f"⚠️  인덱스 상태 확인 중 오류: {e}")
        
        if i < max_retries - 1:
            print(".", end="", flush=True)
            time.sleep(2)
        else:
            print(f"\n❌ 인덱스 준비 시간 초과 ({max_retries * 2}초)")
            return False
    
    return False

if __name__ == "__main__":
    print("🚀 Pinecone 인덱스 초기화 시작")
    print("=" * 50)
    
    # 환경 변수 확인
    required_vars = ["PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        exit(1)
    
    # 사용자 확인
    print(f"⚠️  다음 인덱스의 모든 데이터가 삭제됩니다:")
    print(f"   인덱스명: {os.getenv('PINECONE_INDEX_NAME')}")
    print(f"   기존 차원: 384 → 새 차원: 1536")
    print()
    
    confirm = input("계속하시겠습니까? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ 작업이 취소되었습니다.")
        exit(0)
    
    # 인덱스 초기화 실행
    if reset_pinecone_index():
        print("\n🎉 Pinecone 인덱스 초기화 완료!")
        print("📝 이제 봇을 실행하면 새로운 1536차원 임베딩으로 작동합니다.")
    else:
        print("\n❌ 인덱스 초기화에 실패했습니다.")
        exit(1) 