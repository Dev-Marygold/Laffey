"""
Memory Manager for Laffey's 3-layer memory system.
Manages working memory, episodic memory (Pinecone), and semantic memory (JSON/SQLite).
"""

import os
import json
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
import time

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
import numpy as np

from core.models import (
    WorkingMemoryItem, EpisodicMemoryItem, SemanticFact,
    CoreIdentity, MemorySearchQuery, MemoryType,
    MemoryConsolidationResult
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages Laffey's 3-layer memory system:
    1. Working Memory (Layer 1): Recent chat history in memory
    2. Episodic Memory (Layer 2): Vector database (Pinecone)
    3. Semantic Memory (Layer 3): Structured facts (JSON/SQLite)
    """
    
    def __init__(self):
        """Initialize the memory manager with all three memory layers."""
        # Layer 1: Working Memory (in-memory storage)
        self.working_memory: Dict[str, List[WorkingMemoryItem]] = {}  # channel_id -> messages
        self.working_memory_limit = 20  # Max messages per channel
        
        # Layer 2: Episodic Memory (Pinecone)
        self.vector_store = None
        self.pinecone_ready = False
        self.pinecone_init_task = None
        
        # Start Pinecone initialization in background
        if os.getenv("PINECONE_API_KEY"):
            self.pinecone_init_task = asyncio.create_task(self._async_init_pinecone())
        else:
            logger.warning("PINECONE_API_KEY not set. Episodic memory will be disabled.")
        
        # Layer 3: Semantic Memory (JSON/SQLite)
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.core_identity_path = self.data_dir / "core_identity.json"
        self.semantic_db_path = self.data_dir / "semantic_memory.db"
        
        # Initialize core identity
        self.core_identity = self._load_core_identity()
        
        # Initialize semantic database
        asyncio.create_task(self._init_semantic_db())
        
    def _init_pinecone(self):
        """Initialize Pinecone vector database connection."""
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.warning("PINECONE_API_KEY not set. Episodic memory will be disabled.")
            self.vector_store = None
            return
            
        try:
            logger.info("Starting Pinecone initialization...")
            
            # Initialize Pinecone
            pc = Pinecone(api_key=api_key)
            logger.info("Pinecone client created")
            
            index_name = os.getenv("PINECONE_INDEX_NAME", "laffey-memories")
            
            # Create index if it doesn't exist
            existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
            logger.info(f"Existing indexes: {existing_indexes}")
            
            if index_name not in existing_indexes:
                logger.info(f"Creating new index: {index_name}")
                
                # Pinecone serverless regions
                region = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
                    
                pc.create_index(
                    name=index_name,
                    dimension=1536,  # Dimension for OpenAI text-embedding-3-small
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=region
                    )
                )
                logger.info(f"Index {index_name} created, waiting for it to be ready...")
                
                # Wait for index to be ready
                max_retries = 30
                for i in range(max_retries):
                    try:
                        index_info = pc.describe_index(index_name)
                        if index_info.status.ready:
                            logger.info(f"Index {index_name} is ready!")
                            break
                    except Exception:
                        pass
                    
                    if i < max_retries - 1:
                        time.sleep(2)
                    else:
                        logger.error(f"Index {index_name} failed to become ready after {max_retries * 2} seconds")
                        raise Exception("Index creation timeout")
                
            else:
                logger.info(f"Using existing index: {index_name}")
                
            # Initialize OpenAI embeddings
            logger.info("Initializing OpenAI embeddings...")
            
            # Check for OpenAI API key
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=openai_key,
                chunk_size=1000,  # Number of documents to embed in each request
                max_retries=3,
                timeout=30.0
            )
            logger.info("OpenAI embeddings initialized successfully")
                
            # Get the index
            index = pc.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
            
            # Initialize vector store
            self.vector_store = PineconeVectorStore(
                index=index,
                embedding=embeddings
            )
            logger.info("Pinecone vector store initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}", exc_info=True)
            self.vector_store = None
        
    async def _async_init_pinecone(self):
        """Asynchronously initialize Pinecone vector database connection."""
        try:
            # Run the sync initialization in a thread pool to avoid blocking
            await asyncio.to_thread(self._init_pinecone)
            self.pinecone_ready = True
            logger.info("Pinecone initialization completed in background")
        except Exception as e:
            logger.error(f"Background Pinecone initialization failed: {e}", exc_info=True)
            self.pinecone_ready = False
            
    async def wait_for_pinecone(self, timeout: float = 30.0) -> bool:
        """Wait for Pinecone to be ready with a timeout."""
        if self.pinecone_ready:
            return True
            
        if not self.pinecone_init_task:
            return False
            
        try:
            await asyncio.wait_for(self.pinecone_init_task, timeout=timeout)
            return self.pinecone_ready
        except asyncio.TimeoutError:
            logger.warning(f"Pinecone initialization timed out after {timeout} seconds")
            return False
        
    def _load_core_identity(self) -> CoreIdentity:
        """Load core identity from JSON file or create default."""
        if self.core_identity_path.exists():
            try:
                with open(self.core_identity_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return CoreIdentity(**data)
            except Exception as e:
                logger.error(f"Error loading core identity: {e}")
                
        # Create default identity
        creator_name = os.getenv("CREATOR_NAME", "Unknown")
        identity = CoreIdentity(creator=creator_name)
        self._save_core_identity(identity)
        return identity
        
    def _save_core_identity(self, identity: CoreIdentity):
        """Save core identity to JSON file."""
        try:
            with open(self.core_identity_path, 'w', encoding='utf-8') as f:
                json.dump(identity.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving core identity: {e}")
            
    async def _init_semantic_db(self):
        """Initialize SQLite database for semantic memory."""
        async with aiosqlite.connect(self.semantic_db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source_memory_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_subject ON semantic_facts(subject)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_fact_type ON semantic_facts(fact_type)
            """)
            await db.commit()
    
    # Layer 1: Working Memory Operations
    
    def add_to_working_memory(self, channel_id: str, message: WorkingMemoryItem):
        """Add a message to working memory for a channel."""
        if channel_id not in self.working_memory:
            self.working_memory[channel_id] = []
            
        self.working_memory[channel_id].append(message)
        
        # Trim if exceeds limit
        if len(self.working_memory[channel_id]) > self.working_memory_limit:
            self.working_memory[channel_id] = self.working_memory[channel_id][-self.working_memory_limit:]
            
    def get_working_memory(self, channel_id: str) -> List[WorkingMemoryItem]:
        """Get working memory for a channel."""
        return self.working_memory.get(channel_id, [])
        
    def clear_working_memory(self, channel_id: str):
        """Clear working memory for a channel."""
        if channel_id in self.working_memory:
            self.working_memory[channel_id] = []
            
    # Layer 2: Episodic Memory Operations
    
    async def add_episodic_memory(self, memory: EpisodicMemoryItem) -> str:
        """
        Add an episodic memory to Pinecone vector database.
        
        Args:
            memory: The episodic memory to store
            
        Returns:
            The ID of the stored memory
        """
        # Wait for Pinecone to be ready (with timeout)
        if not self.pinecone_ready:
            logger.info("Waiting for Pinecone initialization...")
            ready = await self.wait_for_pinecone(timeout=10.0)
            if not ready:
                logger.warning("Pinecone not ready. Skipping episodic memory storage.")
                return ""
                
        if not self.vector_store:
            logger.warning("Vector store not initialized. Cannot add episodic memory.")
            return ""
            
        try:
            # Create text representation for embedding
            text = f"User {memory.user_name}: {memory.user_message}\nLaffey: {memory.bot_response}"
            
            # Create metadata
            metadata = {
                "user_id": memory.user_id,
                "user_name": memory.user_name,
                "channel_id": memory.channel_id,
                "timestamp": memory.timestamp.isoformat(),
                "user_message": memory.user_message,
                "bot_response": memory.bot_response,
                "relevance_score": memory.relevance_score,
                "memory_type": memory.memory_type,  # Add memory_type to metadata
                "emotional_tone": memory.emotional_tone,
                "topic_keywords": memory.topic_keywords
            }
            metadata.update(memory.metadata)
            
            # Add to vector store
            ids = await asyncio.to_thread(
                self.vector_store.add_texts,
                texts=[text],
                metadatas=[metadata]
            )
            
            memory.embedding_id = ids[0]
            return ids[0]
            
        except Exception as e:
            logger.error(f"Error adding episodic memory: {e}")
            return ""
            
    async def search_learned_knowledge(
        self,
        query: MemorySearchQuery
    ) -> List[EpisodicMemoryItem]:
        """
        Search specifically for learned knowledge (entries with [LEARN] tag).
        
        Args:
            query: Search query parameters
            
        Returns:
            List of relevant learned knowledge memories
        """
        if not self.vector_store:
            return []
            
        try:
            # Wait for Pinecone to be ready (with shorter timeout for learned knowledge)
            ready = await self.wait_for_pinecone(timeout=10.0)
            if not ready:
                logger.warning("Pinecone not ready for learned knowledge search")
                return []
                
            # Search for memories
            if query.query_text:
                # Search with query text
                results = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score,
                    query.query_text,
                    k=query.limit * 2,  # Get more results to filter
                    filter={
                        "memory_type": "learned_knowledge"  # Simplified filter for learned knowledge
                    }
                )
            else:
                # Get all learned knowledge (use generic query)
                results = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score,
                    "knowledge learning",  # Generic query to get all
                    k=query.limit * 3,  # Get even more results when no specific query
                    filter={
                        "memory_type": "learned_knowledge"  # Simplified filter for learned knowledge
                    }
                )
            
            # Convert to EpisodicMemoryItem objects
            memories = []
            for doc, score in results:
                metadata = doc.metadata
                
                # Skip if not actually learned knowledge
                if not metadata.get("user_message", "").startswith("[LEARN]"):
                    continue
                    
                memory = EpisodicMemoryItem(
                    id=doc.id,  # Use the document ID from Pinecone
                    embedding_id=doc.id,  # Also set embedding_id for compatibility
                    user_id=metadata.get("user_id", ""),
                    user_name=metadata.get("user_name", ""),
                    channel_id=metadata.get("channel_id", ""),
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.utcnow().isoformat())),
                    user_message=metadata.get("user_message", ""),
                    bot_response=metadata.get("bot_response", ""),
                    emotional_tone=metadata.get("emotional_tone", "neutral"),
                    topic_keywords=metadata.get("topic_keywords", []),
                    memory_type=metadata.get("memory_type", "learned_knowledge"),
                    relevance_score=float(1 - score) * 2.0  # Boost relevance for learned knowledge
                )
                memories.append(memory)
                
            # Sort by relevance and limit
            memories.sort(key=lambda m: m.relevance_score, reverse=True)
            return memories[:query.limit]
            
        except Exception as e:
            logger.error(f"Error searching learned knowledge: {e}")
            return []
    
    async def delete_episodic_memory(self, embedding_id: str) -> bool:
        """
        Delete an episodic memory from Pinecone by its embedding ID.
        
        Args:
            embedding_id: The ID of the memory to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vector_store or not embedding_id:
            return False
            
        try:
            # Wait for Pinecone to be ready
            ready = await self.wait_for_pinecone(timeout=5.0)
            if not ready:
                logger.warning("Pinecone not ready for deletion")
                return False
                
            # Get the Pinecone index
            index_name = os.getenv("PINECONE_INDEX_NAME", "laffey-memories")
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index = pc.Index(index_name)
            
            # Delete the vector
            await asyncio.to_thread(index.delete, ids=[embedding_id])
            logger.info(f"Deleted memory with ID: {embedding_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting episodic memory: {e}")
            return False
    
    async def update_episodic_memory(self, embedding_id: str, updated_memory: EpisodicMemoryItem) -> bool:
        """
        Update an existing episodic memory in Pinecone.
        
        Args:
            embedding_id: The ID of the memory to update
            updated_memory: The updated memory content
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vector_store or not embedding_id:
            return False
            
        try:
            # Wait for Pinecone to be ready
            ready = await self.wait_for_pinecone(timeout=10.0)
            if not ready:
                logger.warning("Pinecone not ready for update")
                return False
                
            # First, delete the old memory
            delete_success = await self.delete_episodic_memory(embedding_id)
            if not delete_success:
                logger.error(f"Failed to delete old memory {embedding_id} during update")
                return False
                
            # Then add the updated memory with the same ID
            # Create text representation for embedding
            text = f"User {updated_memory.user_name}: {updated_memory.user_message}\nLaffey: {updated_memory.bot_response}"
            
            # Create metadata
            metadata = {
                "user_id": updated_memory.user_id,
                "user_name": updated_memory.user_name,
                "channel_id": updated_memory.channel_id,
                "timestamp": updated_memory.timestamp.isoformat(),
                "user_message": updated_memory.user_message,
                "bot_response": updated_memory.bot_response,
                "relevance_score": updated_memory.relevance_score,
                "memory_type": updated_memory.memory_type,
                "emotional_tone": updated_memory.emotional_tone,
                "topic_keywords": updated_memory.topic_keywords
            }
            metadata.update(updated_memory.metadata)
            
            # Use the vector store's add_texts method with specific ID
            ids = await asyncio.to_thread(
                self.vector_store.add_texts,
                texts=[text],
                metadatas=[metadata],
                ids=[embedding_id]  # Use the same ID
            )
            
            if ids and ids[0] == embedding_id:
                logger.info(f"Successfully updated memory with ID: {embedding_id}")
                return True
            else:
                logger.error(f"Failed to add updated memory with ID: {embedding_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error updating episodic memory: {e}")
            return False
    
    async def search_episodic_memory(
        self, 
        query: MemorySearchQuery
    ) -> List[EpisodicMemoryItem]:
        """
        Search episodic memories based on query parameters.
        
        Args:
            query: Search parameters
            
        Returns:
            List of matching episodic memories
        """
        # Wait for Pinecone to be ready (with timeout)
        if not self.pinecone_ready:
            logger.info("Waiting for Pinecone initialization for search...")
            ready = await self.wait_for_pinecone(timeout=5.0)
            if not ready:
                logger.warning("Pinecone not ready. Returning empty search results.")
                return []
                
        if not self.vector_store:
            return []
            
        try:
            # Build filter
            filter_dict = {}
            if query.user_id:
                filter_dict["user_id"] = query.user_id
            if query.channel_id:
                filter_dict["channel_id"] = query.channel_id
                
            # Perform similarity search if query text provided
            if query.query_text:
                results = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score,
                    query.query_text,
                    k=query.limit,
                    filter=filter_dict if filter_dict else None
                )
            else:
                # If no query text, just retrieve recent memories with filters
                # This is a limitation of Pinecone - it requires a query
                # So we use a generic query
                results = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score,
                    "recent conversation",
                    k=query.limit,
                    filter=filter_dict if filter_dict else None
                )
                
            # Convert results to EpisodicMemoryItem objects
            memories = []
            for doc, score in results:
                metadata = doc.metadata
                memory = EpisodicMemoryItem(
                    id=doc.id,  # Use the document ID from Pinecone
                    embedding_id=doc.id,  # Also set embedding_id for compatibility
                    user_message=metadata.get("user_message", ""),
                    bot_response=metadata.get("bot_response", ""),
                    user_id=metadata.get("user_id", ""),
                    user_name=metadata.get("user_name", ""),
                    channel_id=metadata.get("channel_id", ""),
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.utcnow().isoformat())),
                    relevance_score=score,
                    memory_type=metadata.get("memory_type", "episodic"),
                    emotional_tone=metadata.get("emotional_tone", "neutral"),
                    topic_keywords=metadata.get("topic_keywords", []),
                    metadata={k: v for k, v in metadata.items() if k not in 
                             ["user_message", "bot_response", "user_id", "user_name", "channel_id", "timestamp", 
                              "memory_type", "emotional_tone", "topic_keywords"]}
                )
                memories.append(memory)
                
            return memories
            
        except Exception as e:
            logger.error(f"Error searching episodic memory: {e}")
            return []
    
    # Layer 3: Semantic Memory Operations
    
    async def add_semantic_fact(self, fact: SemanticFact):
        """Add or update a semantic fact in the database."""
        async with aiosqlite.connect(self.semantic_db_path) as db:
            # Check if fact already exists
            cursor = await db.execute(
                "SELECT id FROM semantic_facts WHERE subject = ? AND fact_type = ? AND content = ?",
                (fact.subject, fact.fact_type, fact.content)
            )
            existing = await cursor.fetchone()
            
            if existing:
                # Update existing fact
                await db.execute(
                    """UPDATE semantic_facts 
                    SET confidence = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?""",
                    (fact.confidence, existing[0])
                )
            else:
                # Insert new fact
                source_ids = json.dumps(fact.source_memory_ids)
                await db.execute(
                    """INSERT INTO semantic_facts 
                    (fact_type, subject, content, confidence, source_memory_ids)
                    VALUES (?, ?, ?, ?, ?)""",
                    (fact.fact_type, fact.subject, fact.content, fact.confidence, source_ids)
                )
                
            await db.commit()
            
    async def get_semantic_facts(
        self, 
        subject: Optional[str] = None,
        fact_type: Optional[str] = None
    ) -> List[SemanticFact]:
        """Retrieve semantic facts from the database."""
        async with aiosqlite.connect(self.semantic_db_path) as db:
            query = "SELECT * FROM semantic_facts WHERE 1=1"
            params = []
            
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            if fact_type:
                query += " AND fact_type = ?"
                params.append(fact_type)
                
            query += " ORDER BY confidence DESC, last_updated DESC"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            facts = []
            for row in rows:
                fact = SemanticFact(
                    fact_type=row[1],
                    subject=row[2],
                    content=row[3],
                    confidence=row[4],
                    source_memory_ids=json.loads(row[5]) if row[5] else [],
                    created_at=datetime.fromisoformat(row[6]),
                    last_updated=datetime.fromisoformat(row[7])
                )
                facts.append(fact)
                
            return facts
    
    # Memory Consolidation
    
    async def consolidate_memories(
        self, 
        channel_id: str,
        llm_interface: Any  # Avoid circular import
    ) -> MemoryConsolidationResult:
        """
        Consolidate working memories into episodic and semantic memories.
        This is the process that transforms short-term memories into long-term storage.
        
        Args:
            channel_id: The channel to consolidate memories for
            llm_interface: The LLM interface for summarization and extraction
            
        Returns:
            Result of the consolidation process
        """
        result = MemoryConsolidationResult()
        start_time = datetime.utcnow()
        
        try:
            # Get working memory for the channel
            working_memories = self.get_working_memory(channel_id)
            if not working_memories:
                result.summary = "No memories to consolidate"
                return result
                
            result.processed_messages = len(working_memories)
            
            # Group messages into conversation chunks
            conversations = self._group_into_conversations(working_memories)
            
            for conv in conversations:
                # Summarize the conversation
                summary = await llm_interface.summarize_conversation(conv)
                
                # Create episodic memories from key moments
                for i in range(0, len(conv) - 1, 2):  # Process in pairs
                    if i + 1 < len(conv) and not conv[i].is_bot_response and conv[i + 1].is_bot_response:
                        memory = EpisodicMemoryItem(
                            user_message=conv[i].content,
                            bot_response=conv[i + 1].content,
                            user_id=conv[i].user_id,
                            user_name=conv[i].user_name,
                            channel_id=channel_id,
                            timestamp=conv[i].timestamp,
                            metadata={"summary": summary}
                        )
                        
                        memory_id = await self.add_episodic_memory(memory)
                        if memory_id:
                            result.episodic_memories_created += 1
                            
                # Extract semantic facts
                facts_data = await llm_interface.extract_facts(summary)
                for fact_data in facts_data:
                    fact = SemanticFact(
                        fact_type=fact_data.get("fact_type", "general"),
                        subject=fact_data.get("subject", "unknown"),
                        content=fact_data.get("content", ""),
                        confidence=fact_data.get("confidence", 0.8),
                        source_memory_ids=[]  # Could link to episodic memories
                    )
                    await self.add_semantic_fact(fact)
                    result.semantic_facts_extracted += 1
                    
            # Clear working memory after consolidation
            self.clear_working_memory(channel_id)
            
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.summary = f"Successfully consolidated {result.processed_messages} messages into {result.episodic_memories_created} episodic memories and {result.semantic_facts_extracted} semantic facts"
            
        except Exception as e:
            logger.error(f"Error during memory consolidation: {e}")
            result.errors.append(str(e))
            result.summary = f"Consolidation failed with error: {str(e)}"
            
        return result
        
    def _group_into_conversations(
        self, 
        messages: List[WorkingMemoryItem],
        gap_minutes: int = 30
    ) -> List[List[WorkingMemoryItem]]:
        """Group messages into conversations based on time gaps."""
        if not messages:
            return []
            
        conversations = []
        current_conv = [messages[0]]
        
        for i in range(1, len(messages)):
            time_gap = (messages[i].timestamp - messages[i-1].timestamp).total_seconds() / 60
            
            if time_gap > gap_minutes:
                # Start new conversation
                conversations.append(current_conv)
                current_conv = [messages[i]]
            else:
                current_conv.append(messages[i])
                
        if current_conv:
            conversations.append(current_conv)
            
        return conversations
    
    # Utility methods
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        stats = {
            "working_memory_channels": len(self.working_memory),
            "working_memory_total_messages": sum(len(msgs) for msgs in self.working_memory.values()),
            "episodic_memory_enabled": self.vector_store is not None,
            "core_identity": self.core_identity.model_dump()
        }
        
        return stats
    
    async def clear_all_memories(self) -> Dict[str, Any]:
        """
        Clear ALL memories from all three layers.
        This is a destructive operation and should be used with caution.
        
        Returns:
            Dictionary with statistics of what was cleared
        """
        result = {
            "working_memory_cleared": 0,
            "episodic_memories_cleared": 0,
            "semantic_facts_cleared": 0,
            "errors": []
        }
        
        try:
            # Layer 1: Clear all working memory
            channel_count = len(self.working_memory)
            message_count = sum(len(msgs) for msgs in self.working_memory.values())
            self.working_memory.clear()
            result["working_memory_cleared"] = message_count
            logger.info(f"Cleared {message_count} messages from {channel_count} channels in working memory")
            
            # Layer 2: Clear episodic memory (Pinecone)
            if self.pinecone_ready and self.vector_store:
                try:
                    # Get Pinecone index and delete all vectors
                    index_name = os.getenv("PINECONE_INDEX_NAME", "laffey-memories")
                    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                    index = pc.Index(index_name)
                    
                    # Delete all vectors
                    await asyncio.to_thread(index.delete, delete_all=True)
                    result["episodic_memories_cleared"] = "all"
                    logger.info("Cleared all vectors from Pinecone index")
                except Exception as e:
                    error_msg = f"Error clearing Pinecone: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            else:
                logger.warning("Pinecone not initialized, skipping episodic memory clear")
                
            # Layer 3: Clear semantic memory (SQLite)
            async with aiosqlite.connect(self.semantic_db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM semantic_facts")
                count = await cursor.fetchone()
                fact_count = count[0] if count else 0
                
                await db.execute("DELETE FROM semantic_facts")
                await db.commit()
                result["semantic_facts_cleared"] = fact_count
                logger.info(f"Cleared {fact_count} semantic facts from database")
                
        except Exception as e:
            error_msg = f"Error during memory clear: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            
        return result 