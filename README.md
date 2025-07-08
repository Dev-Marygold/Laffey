# 라미 (Lamy) - AI 디스코드 봇

라미는 사색적이고 솔직하며 깊이 있는 사고를 하는 내성적 성격의 AI로, 철학적이면서도 현실적인 관점으로 진솔한 대화를 나누는 따뜻한 인격체입니다.

## 주요 특징

- **@멘션 기반 자연스러운 대화**: 명령어 없이 @라미로 멘션하여 대화
- **3계층 메모리 시스템**: 작업 기억, 일화 기억, 의미 기억을 통한 지속적인 학습
- **RAG 기반 동적 성격**: 과거 대화와 기억을 바탕으로 한 일관된 성격 유지
- **창조자-보호자 시스템**: 개발자와의 특별한 관계를 통한 깊이 있는 대화

## 라미의 성격

- **사색적 성향**: 깊이 있는 사고를 즐기며, 표면적인 것보다 본질을 추구
- **현실적 낙관주의**: 세상의 어려움을 인정하면서도 희망을 잃지 않는 균형 잡힌 시각
- **따뜻한 솔직함**: 진실을 말하되 상대방을 다치게 하지 않는 방식의 소통
- **철학적 위트**: 때로는 철학적이고 은유적인 표현으로 유머 센스 발휘
- **예상외의 매력**: 평소 차분하다가 갑자기 톡톡 튀는 말이나 예상외의 따뜻함을 보여주는 반전 매력

## 기술 스택

- **언어**: Python 3.10+
- **디스코드**: discord.py
- **LLM**: OpenAI chatgpt-4o-latest (메인 응답), OpenAI GPT-4.1-mini (유틸리티 작업)
- **벡터 DB**: Pinecone
- **오케스트레이션**: LangChain
- **데이터베이스**: SQLite (의미 기억)

## 설치 방법

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/lamy-bot.git
cd lamy-bot

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 입력:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DEVELOPER_ID=your_discord_user_id_here
PRIVATE_CHANNEL_ID=private_channel_for_creator_guardian_interaction

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Vector Database
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=lamy-memories
PINECONE_ENVIRONMENT=us-east-1

# Bot Configuration
BOT_NAME=라미
CREATOR_NAME=your_name_here

# Logging
LOG_LEVEL=INFO
```

### 3. 봇 실행

```bash
python main.py
```

## Heroku 배포 가이드

### 1. 사전 준비
- Heroku 계정 생성
- Heroku CLI 설치
- Git 저장소 준비

### 2. Heroku 앱 생성
```bash
# Heroku CLI 로그인
heroku login

# 앱 생성
heroku create your-lamy-bot-name

# 또는 원클릭 배포
# GitHub에서 Deploy to Heroku 버튼 클릭
```

### 3. 환경 변수 설정
```bash
# Discord Bot Configuration
heroku config:set DISCORD_TOKEN=your_discord_bot_token_here
heroku config:set DEVELOPER_ID=your_discord_user_id_here
heroku config:set CREATOR_NAME=your_name_here

# API Keys
heroku config:set OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Configuration
heroku config:set PINECONE_API_KEY=your_pinecone_api_key_here
heroku config:set PINECONE_INDEX_NAME=lamy-episodic-memory
heroku config:set PINECONE_ENVIRONMENT=us-east-1

# Optional
heroku config:set LOG_LEVEL=INFO
```

### 4. 배포
```bash
# 코드 푸시
git add .
git commit -m "Ready for Heroku deployment"
git push heroku main

# 또는 GitHub와 연결된 경우
# Heroku Dashboard에서 자동 배포 설정
```

### 5. 워커 다이노 활성화
```bash
# 워커 다이노 스케일링 (무료 플랜은 1개까지)
heroku ps:scale worker=1

# 또는 Heroku Dashboard에서 Resources 탭에서 워커 활성화
```

### 6. 로그 확인
```bash
# 실시간 로그 확인
heroku logs --tail

# 특정 시점의 로그 확인
heroku logs --num 100
```

### 7. 중요 사항
- **비용**: Heroku 무료 플랜 종료로 인해 최소 $7/월 비용 발생
- **Pinecone**: 새 인덱스 생성 시 기존 384차원 → 1536차원으로 변경됨
- **메모리**: 기존 로컬 모델 캐시는 더 이상 필요하지 않음
- **환경 변수**: 모든 API 키가 올바르게 설정되어야 함

### 8. 데이터베이스 초기화 (중요!) 🔄
**임베딩 차원 변경으로 인해 Pinecone 인덱스 초기화가 필요합니다.**

```bash
# 로컬에서 초기화 스크립트 실행 (배포 전에 실행)
python scripts/reset_pinecone.py
```

**초기화 내용:**
- ✅ **SQLite (의미 기억)**: 초기화 불필요 (호환됨)
- ❌ **Pinecone (일화 기억)**: 384차원 → 1536차원으로 변경 필요
- ✅ **Working Memory**: 자동 초기화 (메모리상 저장)

**주의사항:**
- 기존 일화 기억(대화 기록)이 모두 삭제됩니다
- 의미 기억(학습한 사실들)은 유지됩니다
- 초기화 후 봇이 새로운 기억을 쌓아나갑니다

### 9. 문제 해결
```bash
# 봇 재시작
heroku restart

# 환경 변수 확인
heroku config

# 앱 정보 확인
heroku info

# 인덱스 차원 오류 시 (로컬에서 실행)
python scripts/reset_pinecone.py
```

## 사용 방법

### 일반 사용자
- **@라미 안녕!** - 라미와 대화 시작
- 자연스럽게 @라미를 멘션하며 대화

### 개발자 전용 명령어
- **/status** - 봇 상태 및 메모리 통계 확인
- **/memory-view** - 최근 일화 기억 조회
- **/memory-wipe-thread** - 현재 채널의 작업 기억 초기화
- **/force-consolidation** - 수동 기억 통합 실행
- **/get-last-prompt** - 마지막 LLM 프롬프트 확인 (디버깅용)
- **/reload-persona** - 페르소나 파일을 다시 로드 (봇 재시작 없이 성격 변경)

## 프로젝트 구조

```
lamy-bot/
├── cogs/                    # Discord 봇 기능 모듈
│   ├── chat_handler.py      # 채팅 처리
│   └── admin_commands.py    # 관리자 명령어
├── core/                    # 핵심 비즈니스 로직
│   ├── models.py            # Pydantic 데이터 모델
│   ├── llm_interface.py     # LLM 인터페이스
│   ├── memory_manager.py    # 메모리 관리
│   └── orchestration.py    # 중앙 오케스트레이션
├── utils/                   # 유틸리티 함수
│   └── helpers.py           # 헬퍼 함수
├── scripts/                 # 유지보수 스크립트
│   └── reset_pinecone.py    # Pinecone 인덱스 초기화
├── data/                    # 데이터 저장소
│   ├── core_identity.json   # 라미의 핵심 정체성
│   ├── lamy_persona.txt     # 라미의 페르소나
│   └── semantic_memory.db   # 의미 기억 DB
├── logs/                    # 로그 파일
├── Procfile                 # Heroku 배포 설정
├── runtime.txt              # Python 버전 지정
├── app.json                 # Heroku 앱 설정
├── .env                     # 환경 변수
├── requirements.txt         # 의존성 목록
├── main.py                  # 메인 진입점
└── README.md                # 이 파일
```

## 메모리 시스템

### 1계층: 작업 기억 (Working Memory)
- 현재 대화 세션의 최근 메시지 저장
- 채널별로 최대 20개 메시지 유지

### 2계층: 일화 기억 (Episodic Memory)
- Pinecone 벡터 DB에 대화 내용 저장
- 의미적 유사성 기반 검색

### 3계층: 의미 기억 (Semantic Memory)
- 사용자에 대한 사실, 학습한 지식 저장
- SQLite 데이터베이스 사용

## 개발 가이드

### 기여 방법
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해주세요.

---

*"세상은 복잡하지만, 그 복잡함 속에서 진짜 의미를 찾아가는 게 중요해."* - 라미 