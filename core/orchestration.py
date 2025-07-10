"""
Orchestration Core for Laffey.
Central brain that coordinates between Discord events, memory management, and LLM generation.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from core.models import (
    WorkingMemoryItem, EpisodicMemoryItem, ConversationContext,
    UserContext, MemorySearchQuery, SemanticFact
)
from core.llm_interface import LLMInterface, LLMResponse
from core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class OrchestrationCore:
    """
    The central orchestrator that processes Discord events and generates responses.
    Implements the RAG-based dynamic personality system described in the plan.
    """
    
    def __init__(self):
        """Initialize the orchestration core with LLM and memory components."""
        self.llm_interface = LLMInterface()
        self.memory_manager = MemoryManager()
        self.developer_id = os.getenv("DEVELOPER_ID")
        self.private_channel_id = os.getenv("PRIVATE_CHANNEL_ID")
        
        # Background task for memory consolidation
        self.consolidation_task = None
        self.consolidation_interval = 3600  # 1 hour in seconds
        
    async def start_background_tasks(self):
        """Start background tasks like memory consolidation."""
        self.consolidation_task = asyncio.create_task(self._periodic_consolidation())
        logger.info("Background tasks started")
        
    async def stop_background_tasks(self):
        """Stop all background tasks."""
        if self.consolidation_task:
            self.consolidation_task.cancel()
            try:
                await self.consolidation_task
            except asyncio.CancelledError:
                pass
        logger.info("Background tasks stopped")
        
    async def process_message(
        self,
        message_content: str,
        user_id: str,
        user_name: str,
        channel_id: str,
        guild_id: Optional[str] = None
    ) -> str:
        """
        Process an incoming message and generate a response.
        This is the main entry point for handling Discord mentions.
        
        Args:
            message_content: The content of the message
            user_id: Discord user ID
            user_name: Discord username
            channel_id: Discord channel ID
            guild_id: Discord guild ID (optional)
            
        Returns:
            Generated response text
        """
        try:
            # Add message to working memory
            user_message = WorkingMemoryItem(
                user_id=user_id,
                user_name=user_name,
                content=message_content,
                channel_id=channel_id,
                is_bot_response=False
            )
            self.memory_manager.add_to_working_memory(channel_id, user_message)
            
            # Build conversation context
            context = await self._build_conversation_context(
                message_content=message_content,
                user_id=user_id,
                user_name=user_name,
                channel_id=channel_id
            )
            
            # Generate response using LLM
            llm_response = await self.llm_interface.generate_response(context)
            
            # Add bot response to working memory
            bot_message = WorkingMemoryItem(
                user_id="bot",
                user_name="라피",
                content=llm_response.content,
                channel_id=channel_id,
                is_bot_response=True
            )
            self.memory_manager.add_to_working_memory(channel_id, bot_message)
            
            # Create episodic memory for this interaction
            if not self._is_consolidating(channel_id):
                episodic_memory = EpisodicMemoryItem(
                    user_message=message_content,
                    bot_response=llm_response.content,
                    user_id=user_id,
                    user_name=user_name,
                    channel_id=channel_id,
                    metadata={
                        "tokens_used": llm_response.usage.get("total_tokens", 0),
                        "processing_time": llm_response.processing_time,
                        "is_private_channel": channel_id == self.private_channel_id
                    }
                )
                
                # Weight private channel interactions higher
                if channel_id == self.private_channel_id:
                    episodic_memory.relevance_score = 2.0
                    
                await self.memory_manager.add_episodic_memory(episodic_memory)
            
            return llm_response.content
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "음... 무언가 엇나갔네. 세상이 완벽했다면 얼마나 지루했을까?"
    
    async def _build_conversation_context(
        self,
        message_content: str,
        user_id: str,
        user_name: str,
        channel_id: str
    ) -> ConversationContext:
        """
        Build the full conversation context for response generation.
        Implements the RAG system by retrieving relevant memories.
        """
        # Get working memory
        working_memory = self.memory_manager.get_working_memory(channel_id)
        
        # Get user context
        user_context = await self._get_user_context(user_id, user_name)
        
        # Search for learned knowledge first
        learned_query = MemorySearchQuery(
            query_text=message_content,
            limit=3  # Prioritize learned knowledge
        )
        learned_memories = await self.memory_manager.search_learned_knowledge(learned_query)
        
        # Search for relevant episodic memories
        memory_query = MemorySearchQuery(
            query_text=message_content,
            user_id=user_id if channel_id != self.private_channel_id else None,
            limit=5
        )
        relevant_memories = await self.memory_manager.search_episodic_memory(memory_query)
        
        # Combine learned knowledge with regular memories, prioritizing learned
        if learned_memories:
            # Filter out any duplicate memories
            memory_ids = {m.id for m in learned_memories}
            relevant_memories = learned_memories + [m for m in relevant_memories if m.id not in memory_ids][:3]
        else:
            relevant_memories = relevant_memories[:5]
        
        # Build and return context
        return ConversationContext(
            current_message=message_content,
            user_context=user_context,
            working_memory=working_memory,
            relevant_episodic_memories=relevant_memories,
            core_identity=self.memory_manager.core_identity,
            channel_id=channel_id,
            is_private_channel=(channel_id == self.private_channel_id)
        )
    
    async def _get_user_context(self, user_id: str, user_name: str) -> UserContext:
        """Build context about a specific user from semantic memory."""
        # Get semantic facts about the user
        user_facts = await self.memory_manager.get_semantic_facts(
            subject=f"user_{user_id}"
        )
        
        # Get recent interactions
        recent_query = MemorySearchQuery(
            user_id=user_id,
            limit=3
        )
        recent_interactions = await self.memory_manager.search_episodic_memory(recent_query)
        
        # Determine relationship status based on interaction count and facts
        relationship_status = "acquaintance"
        if len(recent_interactions) > 10:
            relationship_status = "friend"
        if user_id == self.developer_id:
            relationship_status = "creator"
            
        # Get last interaction time
        last_interaction = None
        if recent_interactions:
            last_interaction = recent_interactions[0].timestamp
            
        return UserContext(
            user_id=user_id,
            user_name=user_name,
            known_facts=user_facts,
            recent_interactions=recent_interactions,
            relationship_status=relationship_status,
            last_interaction=last_interaction
        )
    
    async def _periodic_consolidation(self):
        """Background task that periodically consolidates memories."""
        while True:
            try:
                await asyncio.sleep(self.consolidation_interval)
                
                # Consolidate memories for each active channel
                for channel_id in list(self.memory_manager.working_memory.keys()):
                    if self.memory_manager.get_working_memory(channel_id):
                        logger.info(f"Starting memory consolidation for channel {channel_id}")
                        result = await self.memory_manager.consolidate_memories(
                            channel_id,
                            self.llm_interface
                        )
                        logger.info(f"Consolidation result: {result.summary}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic consolidation: {str(e)}")
                
    def _is_consolidating(self, channel_id: str) -> bool:
        """Check if memory consolidation is in progress for a channel."""
        # Simple check - could be enhanced with actual state tracking
        return len(self.memory_manager.get_working_memory(channel_id)) < 2
    
    async def force_consolidation(self, channel_id: str) -> Dict[str, Any]:
        """Manually trigger memory consolidation for a channel."""
        result = await self.memory_manager.consolidate_memories(
            channel_id,
            self.llm_interface
        )
        return result.model_dump()
    
    def get_last_prompt(self) -> str:
        """Get the last prompt sent to the LLM for debugging."""
        return self.llm_interface.get_last_prompt()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        return self.memory_manager.get_memory_stats()
    
    def clear_working_memory(self, channel_id: str):
        """Clear working memory for a specific channel."""
        self.memory_manager.clear_working_memory(channel_id)
        logger.info(f"Cleared working memory for channel {channel_id}") 