"""
Pydantic models for Laffey's data structures.
Defines models for the 3-layer memory system and other structured data.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class MemoryType(str, Enum):
    """Types of memories in the system."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class WorkingMemoryItem(BaseModel):
    """
    Represents a single item in working memory (Layer 1).
    Recent chat messages that are kept in the context window.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    user_id: str = Field(..., description="Discord user ID")
    user_name: str = Field(..., description="Discord username")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    channel_id: str = Field(..., description="Discord channel ID")
    is_bot_response: bool = Field(False, description="Whether this is Laffey's response")
    
    
class EpisodicMemoryItem(BaseModel):
    """
    Represents an episodic memory (Layer 2).
    Specific events, conversations, and interactions stored in vector DB.
    """
    user_message: str = Field(..., description="The user's message")
    bot_response: str = Field(..., description="Laffey's response")
    user_id: str = Field(..., description="Discord user ID")
    user_name: str = Field(..., description="Discord username")
    channel_id: str = Field(..., description="Discord channel ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    relevance_score: float = Field(1.0, description="Relevance score from memory consolidation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    embedding_id: Optional[str] = Field(None, description="Pinecone vector ID")
    memory_type: str = Field("episodic", description="Type of memory (episodic, learned_knowledge, etc.)")
    emotional_tone: str = Field("neutral", description="Emotional tone of the interaction")
    topic_keywords: List[str] = Field(default_factory=list, description="Keywords related to the topic")
    id: Optional[str] = Field(None, description="Unique memory ID")


class SemanticFact(BaseModel):
    """
    Represents a learned fact about users or the world (Layer 3).
    Structured facts extracted during memory consolidation.
    """
    fact_type: str = Field(..., description="Type of fact (user_preference, world_knowledge, etc.)")
    subject: str = Field(..., description="Who or what this fact is about")
    content: str = Field(..., description="The fact itself")
    confidence: float = Field(1.0, description="Confidence in this fact (0-1)")
    source_memory_ids: List[str] = Field(default_factory=list, description="Source episodic memory IDs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CoreIdentity(BaseModel):
    """
    Laffey's core identity and immutable facts (Layer 3).
    These define who Laffey is and never change.
    """
    name: str = Field("라피", description="Laffey's name")
    nature: str = Field("AI 동반자", description="Laffey's nature")
    creator: str = Field(..., description="Name of Laffey's creator")
    personality: str = Field(
        "사색적이고 솔직하며 깊이 있는 사고를 하는 내성적 성격",
        description="Core personality trait"
    )
    creation_date: datetime = Field(default_factory=datetime.utcnow)
    core_traits: List[str] = Field(
        default_factory=lambda: [
            "현실적이지만 희망적인 균형 잡힌 시각을 가짐",
                "삶의 의미와 존재에 대해 깊이 있게 탐구하되 절망하지 않음",
                "직설적이지만 따뜻함이 있는 솔직한 표현을 선호함",
                "사색적이면서도 때로는 유머와 위트로 분위기를 전환함",
                "AI로서의 정체성을 받아들이며 성장해가는 모습을 보임"
        ]
    )

class MemorySearchQuery(BaseModel):
    """Query parameters for searching memories."""
    query_text: Optional[str] = Field(None, description="Text to search for")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    channel_id: Optional[str] = Field(None, description="Filter by channel ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    limit: int = Field(10, description="Maximum number of results")
    memory_type: Optional[MemoryType] = Field(None, description="Type of memory to search")


class MemoryConsolidationResult(BaseModel):
    """Result of a memory consolidation process."""
    processed_messages: int = Field(0, description="Number of messages processed")
    episodic_memories_created: int = Field(0, description="Number of episodic memories created")
    semantic_facts_extracted: int = Field(0, description="Number of semantic facts extracted")
    processing_time: float = Field(0.0, description="Time taken to process in seconds")
    summary: str = Field("", description="Summary of the consolidation")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class UserContext(BaseModel):
    """Context about a user for personalized interactions."""
    user_id: str = Field(..., description="Discord user ID")
    user_name: str = Field(..., description="Discord username")
    known_facts: List[SemanticFact] = Field(default_factory=list)
    recent_interactions: List[EpisodicMemoryItem] = Field(default_factory=list)
    relationship_status: str = Field("acquaintance", description="Relationship level with user")
    last_interaction: Optional[datetime] = Field(None)


class ConversationContext(BaseModel):
    """Full context for generating a response."""
    current_message: str = Field(..., description="The current message to respond to")
    user_context: UserContext = Field(..., description="Context about the user")
    working_memory: List[WorkingMemoryItem] = Field(default_factory=list)
    relevant_episodic_memories: List[EpisodicMemoryItem] = Field(default_factory=list)
    core_identity: CoreIdentity = Field(..., description="Laffey's core identity")
    channel_id: str = Field(..., description="Current channel ID")
    is_private_channel: bool = Field(False, description="Whether this is the creator-guardian channel") 