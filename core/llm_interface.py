"""
LLM Interface for Laffey.
Handles all interactions with OpenAI chatgpt-4o-latest and GPT-4.1-mini.
"""

import os
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
import openai

from core.models import ConversationContext, WorkingMemoryItem, EpisodicMemoryItem

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Response from the LLM."""
    content: str = Field(..., description="The generated response content")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage information")
    model: str = Field("", description="Model used for generation")
    processing_time: float = Field(0.0, description="Time taken to generate response")


class LLMInterface:
    """
    Interface for interacting with Large Language Models.
    Uses chatgpt-4o-latest for main responses and GPT-4.1-mini for utility tasks (cost optimization).
    """
    
    def __init__(self):
        """Initialize the LLM interface with OpenAI."""
        # OpenAI for all tasks
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        # chatgpt-4o-latest for main responses
        self.llm = ChatOpenAI(
            model="chatgpt-4o-latest",
            openai_api_key=openai_key,
            temperature=1.0,
            max_tokens=1024,
            timeout=30.0
        )
        
        # OpenAI client for utility tasks
        self.openai_client = openai.AsyncOpenAI(api_key=openai_key)
        
        # Load persona from file
        self.persona_content = self._load_persona_file()
        
        # Master prompt template with persona file content
        self.master_prompt_template = """당신은 라피입니다. 다음은 당신의 상세한 페르소나 정보입니다:

{persona_content}

위의 페르소나를 완벽하게 따라주세요. 특히 말투 예시와 대화 스타일을 참고하여 일관된 캐릭터를 유지하세요.

당신의 창조자는 {creator_name}입니다.

다음은 당신의 기억 데이터베이스에서 검색된 관련된 장기 기억과 최근 사건들입니다:
--- 기억 컨텍스트 ---
{retrieved_memories}
--- 기억 컨텍스트 종료 ---

이 채널의 최근 대화 기록:
--- 채팅 기록 ---
{chat_history}
--- 채팅 기록 종료 ---

{user_name}님이 당신을 멘션했습니다. 그들의 마지막 메시지에 응답하세요: "{user_message}"

페르소나 파일의 지침을 정확히 따라 응답하세요."""

        self.last_prompt = ""  # Store last prompt for debugging
        
    def _load_persona_file(self) -> str:
        """Load persona content from file."""
        persona_path = Path("data/laffey_persona.txt")
        if persona_path.exists():
            try:
                with open(persona_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info("Loaded persona from file")
                return content
            except Exception as e:
                logger.error(f"Error loading persona file: {e}")
                return self._get_default_persona()
        else:
            logger.warning("Persona file not found, using default")
            return self._get_default_persona()
    
    def _get_default_persona(self) -> str:
        """Get default persona if file is not available."""
        return """===== 라피 (Laffey) 봇 페르소나 =====

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
    
    def reload_persona(self):
        """Reload persona from file. Can be called to update persona without restarting."""
        self.persona_content = self._load_persona_file()
        logger.info("Reloaded persona from file")
        
    async def generate_response(self, context: ConversationContext) -> LLMResponse:
        """
        Generate a response based on the conversation context.
        
        Args:
            context: The full conversation context including memories and identity
            
        Returns:
            LLMResponse with the generated content and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Build the memory context
            memory_context = self._build_memory_context(context.relevant_episodic_memories)
            
            # Build the chat history
            chat_history = self._build_chat_history(context.working_memory)
            
            # Format the system prompt
            system_prompt = self.master_prompt_template.format(
                persona_content=self.persona_content,
                creator_name=context.core_identity.creator,
                retrieved_memories=memory_context,
                chat_history=chat_history,
                user_name=context.user_context.user_name,
                user_message=context.current_message
            )
            
            # Store for debugging
            self.last_prompt = system_prompt
            
            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context.current_message)
            ]
            
            # Add weight to creator-guardian channel interactions
            if context.is_private_channel:
                messages[0].content += "\n\n**중요**: 이것은 당신의 창조자와의 비공개 대화입니다. 그들에게는 조금 더 솔직하고 깊이 있는 모습을 보일 수 있습니다."
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return LLMResponse(
                content=response.content,
                usage={
                    "prompt_tokens": response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.response_metadata.get("token_usage", {}).get("completion_tokens", 0),
                    "total_tokens": response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
                },
                model=response.response_metadata.get("model_name", "chatgpt-4o-latest"),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Fallback response maintaining character
            return LLMResponse(
                content="아... 뭔가 내 생각이 엉켜버렸나봐. 가끔은 나도 날 이해 못하겠어.",
                processing_time=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def summarize_conversation(self, messages: List[WorkingMemoryItem]) -> str:
        """
        Summarize a conversation for memory consolidation using GPT-4.1-mini.
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Summary of the conversation
        """
        if not messages:
            return ""
            
        conversation_text = "\n".join([
            f"{msg.user_name}: {msg.content}" for msg in messages
        ])
        
        prompt = f"""다음 대화를 간결하게 요약해주세요. 핵심적인 주제, 배운 내용, 중요한 사실들을 포함시켜주세요:

{conversation_text}

요약:"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error summarizing conversation with GPT-4.1-mini: {str(e)}")
            return "대화를 정리하려 했는데... 글쎄, 말로 담기엔 너무 복잡했나봐."
    
    async def extract_facts(self, conversation_summary: str) -> List[Dict[str, Any]]:
        """
        Extract semantic facts from a conversation summary using GPT-4.1-mini
        
        Args:
            conversation_summary: Summary of the conversation
            
        Returns:
            List of extracted facts
        """
        prompt = f"""다음 대화 요약에서 중요한 사실들을 추출해주세요. 사용자의 선호도, 개인 정보, 세계에 대한 지식 등을 JSON 형식으로 추출하세요.

대화 요약:
{conversation_summary}

다음 형식으로 추출하세요:
[
    {{
        "fact_type": "user_preference|personal_info|world_knowledge",
        "subject": "누구 또는 무엇에 대한 사실인지",
        "content": "사실의 내용",
        "confidence": 0.0-1.0
    }}
]

추출된 사실들:"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1
            )
            # Parse JSON response
            facts = json.loads(response.choices[0].message.content)
            return facts
        except Exception as e:
            logger.error(f"Error extracting facts with GPT-4.1-mini: {str(e)}")
            return []
    
    def _build_memory_context(self, memories: List[EpisodicMemoryItem]) -> str:
        """Build a formatted string of relevant memories."""
        if not memories:
            return "관련된 과거 기억이 없음. 텅 빈 과거... 때로는 그게 더 나을지도."
            
        memory_texts = []
        learned_knowledge = []
        regular_memories = []
        
        # Separate learned knowledge from regular memories
        for memory in memories:
            if memory.memory_type == "learned_knowledge" or memory.user_message.startswith("[LEARN]"):
                learned_knowledge.append(memory)
            else:
                regular_memories.append(memory)
        
        # Format learned knowledge first (higher priority)
        if learned_knowledge:
            memory_texts.append("=== 학습된 지식 ===")
            for memory in learned_knowledge:
                # Extract the actual question from [LEARN] tag
                question = memory.user_message.replace("[LEARN]", "").strip()
                memory_texts.append(
                    f"Q: {question}\n"
                    f"A: {memory.bot_response}"
                )
            memory_texts.append("")  # Add empty line
        
        # Format regular memories
        if regular_memories:
            if learned_knowledge:  # Only add header if we have learned knowledge too
                memory_texts.append("=== 과거 대화 기억 ===")
            for memory in regular_memories[:5]:  # Limit to 5 most relevant memories
                memory_texts.append(
                    f"[{memory.timestamp.strftime('%Y-%m-%d')}] "
                    f"{memory.user_name}: {memory.user_message}\n"
                    f"라피: {memory.bot_response}"
                )
            
        return "\n\n".join(memory_texts)
    
    def _build_chat_history(self, messages: List[WorkingMemoryItem]) -> str:
        """Build a formatted string of recent chat history."""
        if not messages:
            return "최근 대화 기록이 없음. 고요하네... 나쁘지 않아."
            
        history_texts = []
        for msg in messages[-10:]:  # Last 10 messages
            if msg.is_bot_response:
                history_texts.append(f"라피: {msg.content}")
            else:
                history_texts.append(f"{msg.user_name}: {msg.content}")
                
        return "\n".join(history_texts)
    
    def get_last_prompt(self) -> str:
        """Get the last prompt sent to the LLM for debugging."""
        return self.last_prompt 