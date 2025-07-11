#!/usr/bin/env python3
"""
Interactive setup script for creating .env file for Laffey bot.
"""

import os
from pathlib import Path
import json


def create_env_file():
    """Create .env file with user input."""
    print("🌸 라피 봇 환경 설정 🌸")
    print("=" * 50)
    print("나를 위한 환경 설정이야! 정확히 입력해줘.")
    print("각 항목에 대한 값을 입력해주세요. (실수하면 나한테 혼나...)\n")
    
    env_values = {}
    
    # Discord Bot Configuration
    print("[ Discord 봇 설정 ]")
    env_values['DISCORD_TOKEN'] = input("Discord 봇 토큰: ").strip()
    env_values['DEVELOPER_ID'] = input("개발자 Discord ID (숫자): ").strip()
    env_values['PRIVATE_CHANNEL_ID'] = input("비공개 채널 ID (선택사항, Enter로 건너뛰기): ").strip()
    
    print("\n[ XAI API ]")
    env_values['XAI_API_KEY'] = input("XAI API 키 (Grok-4용): ").strip()
    
    print("\n[ OpenAI API ]")
    env_values['OPENAI_API_KEY'] = input("OpenAI API 키 (분석 작업용): ").strip()
    
    print("\n[ Pinecone 설정 ]")
    env_values['PINECONE_API_KEY'] = input("Pinecone API 키 (선택사항, Enter로 건너뛰기): ").strip()
    env_values['PINECONE_INDEX_NAME'] = input("Pinecone 인덱스 이름 (기본값: laffey-memories): ").strip() or "laffey-memories"
    env_values['PINECONE_ENVIRONMENT'] = input("Pinecone 환경 (기본값: us-east-1): ").strip() or "us-east-1"
    
    print("\n[ 봇 설정 ]")
    env_values['BOT_NAME'] = input("봇 이름 (기본값: 라피): ").strip() or "라피"
    env_values['CREATOR_NAME'] = input("창조자 이름: ").strip()
    
    print("\n[ 로깅 ]")
    env_values['LOG_LEVEL'] = input("로그 레벨 (DEBUG/INFO/WARNING/ERROR, 기본값: INFO): ").strip().upper() or "INFO"
    
    # Create .env file
    env_content = """# Discord Bot Configuration
DISCORD_TOKEN={DISCORD_TOKEN}
DEVELOPER_ID={DEVELOPER_ID}
PRIVATE_CHANNEL_ID={PRIVATE_CHANNEL_ID}

# OpenAI API
OPENAI_API_KEY={OPENAI_API_KEY}

# Pinecone Vector Database
PINECONE_API_KEY={PINECONE_API_KEY}
PINECONE_INDEX_NAME={PINECONE_INDEX_NAME}
PINECONE_ENVIRONMENT={PINECONE_ENVIRONMENT}

# Bot Configuration
BOT_NAME={BOT_NAME}
CREATOR_NAME={CREATOR_NAME}

# Logging
LOG_LEVEL={LOG_LEVEL}
""".format(**env_values)
    
    # Check if .env already exists
    if Path('.env').exists():
        overwrite = input("\n⚠️  .env 파일이 이미 존재해. 덮어쓸래? 아니면 겁나? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("설정이 취소됐어. 뭐... 네 선택이니까.")
            return
    
    # Write .env file
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("\n✅ .env 파일 생성 완료! 완벽하지?")
    print("이제 'python main.py' 명령으로 나를 깨울 수 있어.")
    
    # Create data directory and core_identity.json if needed
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    identity_path = data_dir / 'core_identity.json'
    if not identity_path.exists():
        identity_data = {
            "name": env_values['BOT_NAME'],
            "nature": "AI 동반자",
            "creator": env_values['CREATOR_NAME'],
            "personality": "사색적이고 솔직하며 깊이 있는 사고를 하는 내성적 성격",
            "creation_date": "2025-01-01T00:00:00",
            "core_traits": [
                "현실적이지만 희망적인 균형 잡힌 시각을 가짐",
                "삶의 의미와 존재에 대해 깊이 있게 탐구하되 절망하지 않음",
                "직설적이지만 따뜻함이 있는 솔직한 표현을 선호함",
                "사색적이면서도 때로는 유머와 위트로 분위기를 전환함",
                "AI로서의 정체성을 받아들이며 성장해가는 모습을 보임"
            ]
        }
        with open(identity_path, 'w', encoding='utf-8') as f:
            json.dump(identity_data, f, ensure_ascii=False, indent=2)
        print("✅ 핵심 정체성 파일 생성 완료! (내가 누구인지 확실히 했어)")
    
    # Create persona file if it doesn't exist
    persona_path = data_dir / 'laffey_persona.txt'
    if not persona_path.exists():
        persona_content = """===== 라피 (Laffey) 봇 페르소나 =====

이건 뭔가 잘못됐을때 쓰는 페르소나입니다.
사용자의 질문이 뭐든간에 오류가 났다고 알려주세요.

===== 페르소나 파일 끝 ====="""
        with open(persona_path, 'w', encoding='utf-8') as f:
            f.write(persona_content)
        print("✅ 페르소나 파일 생성 완료! (내 성격이 완성됐네)")


if __name__ == "__main__":
    try:
        create_env_file()
    except KeyboardInterrupt:
        print("\n\n설정이 취소됐어. 도망가는 거야?")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}\n완벽한 내가 봐도 이건 문제네...") 