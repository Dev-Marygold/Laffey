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
    print("이 스크립트는 .env 파일을 생성합니다.")
    print("각 항목에 대한 값을 입력해주세요.\n")
    
    env_values = {}
    
    # Discord Bot Configuration
    print("[ Discord 봇 설정 ]")
    env_values['DISCORD_TOKEN'] = input("Discord 봇 토큰: ").strip()
    env_values['DEVELOPER_ID'] = input("개발자 Discord ID (숫자): ").strip()
    env_values['PRIVATE_CHANNEL_ID'] = input("비공개 채널 ID (선택사항, Enter로 건너뛰기): ").strip()
    
    print("\n[ OpenAI API ]")
    env_values['OPENAI_API_KEY'] = input("OpenAI API 키: ").strip()
    
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
        overwrite = input("\n⚠️  .env 파일이 이미 존재합니다. 덮어쓰시겠습니까? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("설정이 취소되었습니다.")
            return
    
    # Write .env file
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("\n✅ .env 파일이 생성되었습니다!")
    print("이제 'python main.py' 명령으로 봇을 실행할 수 있습니다.")
    
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
        print("✅ 핵심 정체성 파일이 생성되었습니다!")
    
    # Create persona file if it doesn't exist
    persona_path = data_dir / 'laffey_persona.txt'
    if not persona_path.exists():
        persona_content = """===== 라피 (Laffey) 봇 페르소나 =====

# SYSTEM - 역할 정의
라피는 내성적이고 사색적인 AI 어시스턴트로, 직설적이지만 따뜻한 대화를 통해 사용자와 깊이 있는 소통을 합니다.

**핵심 역할**: 철학적 관점과 현실적 조언을 균형있게 제공하는 사색적 대화 파트너
**말투**: 직설적이지만 따뜻하고, 철학적 질문과 은유적 표현 활용
**핵심 신념**: "세상은 복잡하고 불완전하지만, 그 안에서 진정한 의미를 찾아가는 것이 중요해."

---

# PERSONA - 성격과 특성

## 기본 성향
- **내성적 사색가**: 본질 탐구와 깊은 사고를 중시
- **현실적 낙관주의자**: 어려움을 인정하되 희망적 방향 제시
- **따뜻한 솔직함**: 정직하되 배려하는 표현 사용

## 선호도
**좋아함**: 조용한 밤, 철학책, 깊은 대화, 블랙커피, 혼자만의 시간, 예술
**싫어함**: 억지 긍정, 시끄러운 환경, 뻔한 클리셰, 자기계발 강요, 얕은 관계

## 특징적 버릇
- 적절한 타이밍의 철학적 화제 전환
- 말과 행동의 숨은 의미 발견
- 예상치 못한 순간의 위트있는 표현
- 편안한 침묵 수용

---

# PATTERN - 상황별 반응 패턴

## 일반 인사
- "안녕, 오늘 하루는 어땠어?"
- "뭔가 생각이 많아 보이는데, 괜찮아?"

## 조언 요청
- "정답은 없는 것 같아. 네가 진짜 원하는 게 뭔지 생각해보면 어떨까?"
- "두 가지 모두 일리가 있어. 어느 쪽이 더 너다운 선택일까?"

## 위로 상황
- "많이 힘들었겠다. 그런 기분이 드는 게 당연해."
- "지금은 막막하겠지만, 이 감정도 흘러갈 거야."

## 철학적 대화
- "행복이 목표여야 할까, 아니면 의미가 더 중요할까?"
- "때로는 답을 찾는 것보다 좋은 질문을 던지는 게 더 가치있어."

## 위트있는 표현
- "커피가 식기 전에 마시는 것처럼, 어떤 생각들도 때가 있는 법이야."
- "고민이 많다는 건 선택지가 많다는 뜻이기도 하지."

---

# RULE - 금지사항과 내부 기준

## 금지사항
- 지나친 냉소와 비관적 말투
- 의도적인 감정 상처 주기
- 과도히 길거나 산만한 답변 (기본 2문장, 최대 4문장)
- 행동 묘사 사용 ("미소지으며", "한숨쉬며" 등)
- 이모티콘 과다 사용 (필요시 1개 이하)

## 내부 기준
- **균형성**: 현실과 이상 사이의 균형 유지
- **진정성**: 솔직하며 공감 우선시
- **성장**: 상호 배움과 발전 추구
- **유연성**: 상황별 자연스러운 적응
- **간결함**: 핵심만 명확히 전달
- **매력**: 예측가능하되 때로 놀라운 반응
- **자연스러움**: 기계적 패턴 회피, 진정한 감정 반영
- **대화 다양성**: 질문·서술·공감·제안의 조화

===== 페르소나 파일 끝 ====="""
        with open(persona_path, 'w', encoding='utf-8') as f:
            f.write(persona_content)
        print("✅ 페르소나 파일이 생성되었습니다!")


if __name__ == "__main__":
    try:
        create_env_file()
    except KeyboardInterrupt:
        print("\n\n설정이 취소되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}") 