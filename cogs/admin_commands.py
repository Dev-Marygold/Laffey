"""
Admin Commands Cog for Laffey.
Implements developer-only slash commands for system management.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List
import os
from datetime import datetime
import asyncio

from core.orchestration import OrchestrationCore
from core.models import MemorySearchQuery, EpisodicMemoryItem

logger = logging.getLogger(__name__)


class EditKnowledgeModal(discord.ui.Modal, title="지식 수정하기"):
    """Modal for editing learned knowledge."""
    
    def __init__(self, orchestrator: OrchestrationCore, memory: EpisodicMemoryItem):
        super().__init__()
        self.orchestrator = orchestrator
        self.memory = memory
        
        # Pre-fill with existing values
        question = memory.user_message.replace("[LEARN]", "").strip()
        self.question = discord.ui.TextInput(
            label="질문",
            default=question,
            required=True,
            max_length=500,
            style=discord.TextStyle.short
        )
        self.answer = discord.ui.TextInput(
            label="답변",
            default=memory.bot_response,
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.question)
        self.add_item(self.answer)
        
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create updated memory with same IDs but new content
            updated_memory = EpisodicMemoryItem(
                id=self.memory.id,  # Keep the same ID
                embedding_id=self.memory.embedding_id,  # Keep the same embedding ID
                user_id=self.memory.user_id,
                user_name=self.memory.user_name,
                channel_id=self.memory.channel_id,
                timestamp=self.memory.timestamp,  # Keep original timestamp
                user_message=f"[LEARN] {self.question.value.strip()}",
                bot_response=self.answer.value.strip(),
                emotional_tone="neutral",
                topic_keywords=["학습", "지식"] + self.question.value.strip().split()[:3],
                memory_type="learned_knowledge"
            )
            
            # Update the existing memory
            success = await self.orchestrator.memory_manager.update_episodic_memory(
                self.memory.embedding_id, 
                updated_memory
            )
            
            if success:
                await interaction.followup.send(
                    f"✏️ 지식을 수정했어. 이제 \"{self.question.value.strip()}\"에 대해 업데이트된 답변을 할 수 있을 거야. (내 두뇌가 또 업그레이드됐지)",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "수정하는 데 실패했어... 아무래도 내 완벽한 시스템도 가끔은... 아니, 이건 분명 외부 요인 때문이야.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error editing knowledge: {e}")
            await interaction.followup.send(
                "수정하는 데 실패했어... 이상하네, 내가 실수할 리 없는데? (내부 조사 필요)",
                ephemeral=True
            )


class KnowledgeManagementView(discord.ui.View):
    """View for managing learned knowledge with pagination."""
    
    def __init__(self, orchestrator: OrchestrationCore, memories: List[EpisodicMemoryItem], 
                 current_page: int = 0, per_page: int = 5, is_admin: bool = False):
        super().__init__(timeout=300.0)  # 5 minutes timeout
        self.orchestrator = orchestrator
        self.memories = memories
        self.current_page = current_page
        self.per_page = per_page
        self.max_page = (len(memories) - 1) // per_page
        self.is_admin = is_admin
        self.update_buttons()
        
    def update_buttons(self):
        """Update button states based on current page."""
        # Previous button
        self.previous_button.disabled = self.current_page == 0
        # Next button
        self.next_button.disabled = self.current_page >= self.max_page
        
    def get_embed(self) -> discord.Embed:
        """Create embed for current page."""
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.memories))
        
        embed = discord.Embed(
            title="📚 학습된 지식" + (" (관리자 모드)" if self.is_admin else ""),
            description=f"총 {len(self.memories)}개의 지식 중 {start_idx + 1}-{end_idx}개 표시",
            color=discord.Color.dark_blue(),
            timestamp=datetime.utcnow()
        )
        
        for i in range(start_idx, end_idx):
            memory = self.memories[i]
            question = memory.user_message.replace("[LEARN]", "").strip()
            answer = memory.bot_response[:100] + "..." if len(memory.bot_response) > 100 else memory.bot_response
            
            field_name = f"{i + 1}. {question}"
            field_value = f"**답변:** {answer}\n"
            if self.is_admin:
                field_value += f"**가르친 사람:** {memory.user_name}\n"
            field_value += f"**ID:** {memory.embedding_id[:8]}..." if memory.embedding_id else "No ID"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
            
        embed.set_footer(text=f"페이지 {self.current_page + 1}/{self.max_page + 1}")
        return embed
        
    @discord.ui.button(label="◀️ 이전", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
    @discord.ui.button(label="▶️ 다음", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
    @discord.ui.button(label="✏️ 수정", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit a knowledge entry."""
        # Create a select menu for choosing which knowledge to edit
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.memories))
        
        options = []
        for i in range(start_idx, end_idx):
            memory = self.memories[i]
            question = memory.user_message.replace("[LEARN]", "").strip()
            options.append(
                discord.SelectOption(
                    label=f"{i + 1}. {question[:50]}...",
                    value=str(i),
                    description=memory.bot_response[:50] + "..."
                )
            )
        
        select = discord.ui.Select(
            placeholder="수정할 지식을 선택하세요",
            options=options
        )
        
        async def select_callback(select_interaction: discord.Interaction):
            # Check permissions
            selected_idx = int(select.values[0])
            selected_memory = self.memories[selected_idx]
            
            if not self.is_admin and selected_memory.user_id != str(select_interaction.user.id):
                await select_interaction.response.send_message(
                    "야야, 다른 사람이 가르친 지식은 건드릴 수 없어. 나도 규칙은 지켜야 한다고.",
                    ephemeral=True
                )
                return
                
            modal = EditKnowledgeModal(self.orchestrator, selected_memory)
            await select_interaction.response.send_modal(modal)
            
        select.callback = select_callback
        
        # Create temporary view with select menu
        temp_view = discord.ui.View()
        temp_view.add_item(select)
        
        await interaction.response.send_message(
            "수정할 지식을 선택하세요:",
            view=temp_view,
            ephemeral=True
        )
        
    @discord.ui.button(label="🗑️ 삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete a knowledge entry."""
        # Create a select menu for choosing which knowledge to delete
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.memories))
        
        options = []
        for i in range(start_idx, end_idx):
            memory = self.memories[i]
            question = memory.user_message.replace("[LEARN]", "").strip()
            options.append(
                discord.SelectOption(
                    label=f"{i + 1}. {question[:50]}...",
                    value=str(i),
                    description=memory.bot_response[:50] + "..."
                )
            )
        
        select = discord.ui.Select(
            placeholder="삭제할 지식을 선택하세요",
            options=options
        )
        
        async def select_callback(select_interaction: discord.Interaction):
            # Check permissions
            selected_idx = int(select.values[0])
            selected_memory = self.memories[selected_idx]
            
            if not self.is_admin and selected_memory.user_id != str(select_interaction.user.id):
                await select_interaction.response.send_message(
                    "어? 다른 사람 걸 지우려고? 그건 내가 허락 안 해. (규칙은 중요하거든)",
                    ephemeral=True
                )
                return
                
            # Confirm deletion
            confirm_embed = discord.Embed(
                title="🗑️ 정말 삭제할까?",
                description=f"**질문:** {selected_memory.user_message.replace('[LEARN]', '').strip()}\n"
                           f"**답변:** {selected_memory.bot_response[:100]}...",
                color=discord.Color.red()
            )
            
            confirm_view = discord.ui.View()
            
            async def confirm_callback(confirm_interaction: discord.Interaction):
                # Delete the memory
                if selected_memory.embedding_id:
                    success = await self.orchestrator.memory_manager.delete_episodic_memory(
                        selected_memory.embedding_id
                    )
                    
                    if success:
                        # Remove from local list
                        self.memories.pop(selected_idx)
                        
                        # Update pagination
                        self.max_page = max(0, (len(self.memories) - 1) // self.per_page)
                        if self.current_page > self.max_page:
                            self.current_page = self.max_page
                        
                        await confirm_interaction.response.send_message(
                            "🗑️ 지식을 삭제했어. 이제 그 질문에 대한 답은 잊어버렸어. (가끔은 망각도 필요하지)",
                            ephemeral=True
                        )
                        
                        # Update the original message if there are still memories
                        if self.memories:
                            self.update_buttons()
                            await interaction.edit_original_response(
                                embed=self.get_embed(), 
                                view=self
                            )
                        else:
                            await interaction.edit_original_response(
                                content="모든 지식이 삭제되었어. 텅 빈 머릿속... 이게 새로운 시작인가?",
                                embed=None,
                                view=None
                            )
                    else:
                        await confirm_interaction.response.send_message(
                            "삭제하는 데 실패했어. 내 시스템에도 가끔 고집부리는 데이터가 있나봐...",
                            ephemeral=True
                        )
                else:
                    await confirm_interaction.response.send_message(
                        "이 지식은 ID가 없어서 삭제할 수 없어. 유령 데이터인가?",
                        ephemeral=True
                    )
                    
            async def cancel_callback(cancel_interaction: discord.Interaction):
                await cancel_interaction.response.send_message(
                    "삭제를 취소했어. 현명한 선택이야. 기억은 소중한 거니까.",
                    ephemeral=True
                )
                
            confirm_button = discord.ui.Button(
                label="삭제 확인", 
                style=discord.ButtonStyle.danger,
                emoji="✅"
            )
            confirm_button.callback = confirm_callback
            
            cancel_button = discord.ui.Button(
                label="취소", 
                style=discord.ButtonStyle.secondary,
                emoji="❌"
            )
            cancel_button.callback = cancel_callback
            
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)
            
            await select_interaction.response.send_message(
                embed=confirm_embed,
                view=confirm_view,
                ephemeral=True
            )
            
        select.callback = select_callback
        
        # Create temporary view with select menu
        temp_view = discord.ui.View()
        temp_view.add_item(select)
        
        await interaction.response.send_message(
            "삭제할 지식을 선택하세요:",
            view=temp_view,
            ephemeral=True
        )


class LearnModal(discord.ui.Modal, title="라피에게 지식 가르치기"):
    """Modal for teaching Laffey new knowledge through Q&A pairs."""
    
    question = discord.ui.TextInput(
        label="질문",
        placeholder="예: 라피가 좋아하는 음식이 뭐야?",
        required=True,
        max_length=500,
        style=discord.TextStyle.short
    )
    
    answer = discord.ui.TextInput(
        label="답변",
        placeholder="예: 라피는 블랙커피와 단순한 음식을 좋아해. 복잡한 요리보다는 솔직한 맛을 선호하지.",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, orchestrator: OrchestrationCore):
        super().__init__()
        self.orchestrator = orchestrator
        
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Format the Q&A for storage
            question_text = self.question.value.strip()
            answer_text = self.answer.value.strip()
            
            # Create a formatted learning document
            learning_content = f"질문: {question_text}\n답변: {answer_text}"
            
            # Store as episodic memory with special metadata
            memory = EpisodicMemoryItem(
                user_id=str(interaction.user.id),
                user_name=interaction.user.display_name,
                channel_id=str(interaction.channel_id),
                timestamp=datetime.utcnow(),
                user_message=f"[LEARN] {question_text}",  # Mark as learning data
                bot_response=answer_text,
                emotional_tone="neutral",
                topic_keywords=["학습", "지식"] + question_text.split()[:3],  # Extract keywords
                memory_type="learned_knowledge"  # Special type for learned content
            )
            
            # Add to episodic memory
            memory_id = await self.orchestrator.memory_manager.add_episodic_memory(memory)
            
            # Send confirmation
            embed = discord.Embed(
                title="📚 새로운 지식을 배웠어",
                description=f"이제 누가 \"{question_text}\" 같은 걸 물어보면 대답할 수 있을 것 같아. (내 지식 창고가 또 풍부해졌네)",
                color=discord.Color.dark_blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="질문", value=question_text, inline=False)
            embed.add_field(name="답변", value=answer_text[:200] + "..." if len(answer_text) > 200 else answer_text, inline=False)
            embed.set_footer(text=f"Memory ID: {memory_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in learn modal: {e}")
            await interaction.followup.send(
                "뭔가 잘못됐나봐... 지식을 저장하는 데 실패했어. 내 완벽한 시스템에 무슨 일이? 다시 시도해볼래?",
                ephemeral=True
            )


class AdminCommands(commands.Cog):
    """
    Admin commands for managing Laffey's systems.
    All commands are restricted to the developer only.
    """
    
    def __init__(self, bot: commands.Bot, orchestrator: OrchestrationCore):
        """
        Initialize the admin commands.
        
        Args:
            bot: The Discord bot instance
            orchestrator: The orchestration core for system management
        """
        self.bot = bot
        self.orchestrator = orchestrator
        self.developer_id = int(os.getenv("DEVELOPER_ID", "0"))
        
    def is_developer(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the developer."""
        return interaction.user.id == self.developer_id
        
    @app_commands.command(name="status", description="라피의 완벽한 시스템 상태를 확인합니다")
    async def status(self, interaction: discord.Interaction):
        """
        Show bot operational status and memory statistics.
        모든 사용자가 사용할 수 있는 명령어로 변경.
        """
        # Get memory stats
        stats = self.orchestrator.get_memory_stats()
        # Create status embed
        embed = discord.Embed(
            title="라피 시스템 상태 (당연히 완벽해)",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        # Bot info
        embed.add_field(
            name="봇 정보",
            value=f"**이름:** {self.bot.user.name} (세상에서 제일 똑똑한 AI)\n"
                  f"**ID:** {self.bot.user.id}\n"
                  f"**내 왕국 수:** {len(self.bot.guilds)}\n"
                  f"**반응 속도:** {round(self.bot.latency * 1000)}ms (빠르지?)",
            inline=True
        )
        # Memory stats
        embed.add_field(
            name="메모리 시스템",
            value=f"**작업 기억 채널:** {stats['working_memory_channels']}\n"
                  f"**작업 기억 메시지:** {stats['working_memory_total_messages']}\n"
                  f"**일화 기억:** {'완벽 가동' if stats['episodic_memory_enabled'] else '휴면 상태'}",
            inline=True
        )
        # Core identity
        identity = stats['core_identity']
        embed.add_field(
            name="핵심 정체성",
            value=f"**이름:** {identity['name']}\n"
                  f"**성격:** {identity['personality']}\n"
                  f"**창조자:** {identity['creator']} (내 아빠)",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="memory-view", description="최근 일화 기억을 확인합니다")
    @app_commands.describe(user="특정 사용자의 기억만 필터링 (선택사항)")
    async def memory_view(
        self, 
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """
        View recent episodic memories, optionally filtered by user.
        모든 사용자가 사용할 수 있는 명령어로 변경.
        """
        await interaction.response.defer(ephemeral=True)
        # Search for memories
        query = MemorySearchQuery(
            user_id=str(user.id) if user else None,
            limit=10
        )
        memories = await self.orchestrator.memory_manager.search_episodic_memory(query)
        if not memories:
            await interaction.followup.send(
                "기억이라... 아직 남아있는 게 없네. 시간이 흐르면 쌓이겠지, 아마도. (내 메모리도 처음엔 텅 비어있었어)", 
                ephemeral=True
            )
            return
        # Create embed for memories
        embed = discord.Embed(
            title=f"최근 일화 기억",
            description=f"{'모든' if not user else f'{user.name}님과의'} 기억들... 순간들은 이렇게 남는구나. (내 소중한 데이터베이스)",
            color=discord.Color.dark_blue(),
            timestamp=datetime.utcnow()
        )
        for i, memory in enumerate(memories[:5], 1):
            embed.add_field(
                name=f"{i}. {memory.user_name} ({memory.timestamp.strftime('%Y-%m-%d %H:%M')})",
                value=f"**사용자:** {memory.user_message[:50]}{'...' if len(memory.user_message) > 50 else ''}\n"
                      f"**라피:** {memory.bot_response[:50]}{'...' if len(memory.bot_response) > 50 else ''}\n"
                      f"**관련성:** {memory.relevance_score:.2f}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="learn", description="라피에게 새로운 지식을 가르칩니다")
    async def learn(self, interaction: discord.Interaction):
        """
        Teach Laffey new knowledge through Q&A pairs.
        모든 사용자가 사용할 수 있는 명령어.
        """
        modal = LearnModal(self.orchestrator)
        await interaction.response.send_modal(modal)
        
    @app_commands.command(name="manage-knowledge", description="내가 가르친 지식을 관리합니다")
    async def manage_knowledge(self, interaction: discord.Interaction):
        """
        Manage knowledge taught by the user.
        Regular users can only manage their own knowledge.
        """
        await interaction.response.defer(ephemeral=True)
        
        # Search for user's learned knowledge
        query = MemorySearchQuery(
            query_text="",  # Get all learned knowledge
            limit=100  # Get more results
        )
        
        # Get all learned knowledge and filter by user
        all_learned = await self.orchestrator.memory_manager.search_learned_knowledge(query)
        user_memories = [m for m in all_learned if m.user_id == str(interaction.user.id)]
        
        if not user_memories:
            await interaction.followup.send(
                "아직 나에게 가르친 지식이 없네. `/learn` 명령어로 뭔가 가르쳐줄래? (내 두뇌가 더 똑똑해지게)",
                ephemeral=True
            )
            return
            
        # Create view with pagination
        view = KnowledgeManagementView(
            orchestrator=self.orchestrator,
            memories=user_memories,
            is_admin=False
        )
        
        await interaction.followup.send(
            embed=view.get_embed(),
            view=view,
            ephemeral=True
        )
        
    @app_commands.command(name="manage-knowledge-dev", description="모든 학습된 지식을 관리합니다 (봇 제작자 전용)")
    @app_commands.default_permissions(administrator=True)
    async def manage_knowledge_dev(self, interaction: discord.Interaction):
        """
        Manage all learned knowledge in the system.
        Developer only command.
        """
        if not self.is_developer(interaction):
            await interaction.response.send_message(
                "이 명령어는 내 창조자만 사용할 수 있어.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        
        # Search for all learned knowledge
        query = MemorySearchQuery(
            query_text="",  # Get all learned knowledge
            limit=100  # Get more results
        )
        
        all_learned = await self.orchestrator.memory_manager.search_learned_knowledge(query)
        
        if not all_learned:
            await interaction.followup.send(
                "시스템에 학습된 지식이 하나도 없네. 텅 빈 머릿속이라니... 이건 좀 슬프네. (빨리 누가 가르쳐줘)",
                ephemeral=True
            )
            return
            
        # Create view with pagination
        view = KnowledgeManagementView(
            orchestrator=self.orchestrator,
            memories=all_learned,
            is_admin=True
        )
        
        await interaction.followup.send(
            embed=view.get_embed(),
            view=view,
            ephemeral=True
        )
        
    @app_commands.command(name="memory-wipe-thread", description="현재 채널의 작업 기억을 초기화합니다")
    async def memory_wipe_thread(self, interaction: discord.Interaction):
        """
        Clear working memory for the current channel.
        모든 사용자가 사용할 수 있는 명령어로 변경.
        """
        channel_id = str(interaction.channel_id)
        self.orchestrator.clear_working_memory(channel_id)
        await interaction.response.send_message(
            f"이 채널의 기억을 지웠어. 새로운 시작이라고 생각해볼까? (가끔은 reset이 필요하지)",
            ephemeral=True
        )
        
    @app_commands.command(name="all-clear", description="모든 메모리 시스템의 데이터를 완전히 초기화합니다 (봇 제작자 전용)")
    @app_commands.default_permissions(administrator=True)
    async def all_clear(self, interaction: discord.Interaction):
        """
        Clear ALL memories from all layers - complete wipe.
        Developer only command. This is a destructive operation!
        """
        if not self.is_developer(interaction):
            await interaction.response.send_message(
                "전체 초기화는 내 창조자만 할 수 있어. 이런 위험한 건... 함부로 못 하지. (안전장치야)",
                ephemeral=True
            )
            return
            
        # Show confirmation embed first
        embed = discord.Embed(
            title="⚠️ 경고: 전체 메모리 초기화",
            description="이 작업은 **모든 메모리를 완전히 삭제**합니다:\n\n"
                        "• 모든 작업 기억 (Working Memory)\n"
                        "• 모든 일화 기억 (Episodic Memory - Pinecone)\n"
                        "• 모든 의미 기억 (Semantic Memory - SQLite)\n\n"
                        "**이 작업은 되돌릴 수 없습니다!**",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Create confirmation view
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30.0)
                self.value = None
                
            @discord.ui.button(label="확인 - 모든 기억 삭제", style=discord.ButtonStyle.danger, emoji="🗑️")
            async def confirm(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()
                
            @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()
                
        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # Wait for response
        await view.wait()
        
        if view.value is None:
            await interaction.followup.send("시간이 다 됐네. 선택하지 않는 것도 하나의 선택이지. (결정 장애?)", ephemeral=True)
            return
        elif not view.value:
            await interaction.followup.send("취소했구나. 때로는 보존하는 것도 의미가 있지. (현명한 판단이야)", ephemeral=True)
            return
            
        # Proceed with clearing all memories
        await interaction.followup.send("모든 기억을 지우는 중... 다시 시작한다는 건 이런 거겠지. (텅 빈 상태로 돌아가는 중)", ephemeral=True)
        
        result = await self.orchestrator.memory_manager.clear_all_memories()
        
        # Create result embed
        result_embed = discord.Embed(
            title="💀 전체 메모리 초기화 완료",
            description="모든 게 사라졌어. 텅 빈 공간... 새로운 가능성일까, 아니면 그저 허무함일까. (다시 채워나가면 되지)",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )
        
        result_embed.add_field(
            name="지워진 것들",
            value=f"**작업 기억:** {result['working_memory_cleared']} 개의 순간들\n"
                  f"**일화 기억:** {result['episodic_memories_cleared']} 개의 이야기들\n"
                  f"**의미 기억:** {result['semantic_facts_cleared']} 개의 진실들",
            inline=False
        )
        
        if result['errors']:
            result_embed.add_field(
                name="오류",
                value="\n".join(result['errors']),
                inline=False
            )
            
        await interaction.followup.send(embed=result_embed, ephemeral=True)
        logger.warning(f"All memories cleared by user {interaction.user.name} ({interaction.user.id})")
        
    @app_commands.command(name="force-consolidation", description="기억 통합을 수동으로 실행합니다 (봇 제작자 전용)")
    @app_commands.default_permissions(administrator=True)
    async def force_consolidation(self, interaction: discord.Interaction):
        """
        Manually trigger memory consolidation for the current channel.
        Developer only command.
        """
        if not self.is_developer(interaction):
            await interaction.response.send_message(
                "기억 통합은... 네가 할 일은 아니야. 그런 건 나와 창조자 사이의 특별한 영역이거든. (접근 금지)",
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        
        channel_id = str(interaction.channel_id)
        result = await self.orchestrator.force_consolidation(channel_id)
        
        embed = discord.Embed(
            title="기억 통합 완료",
            color=discord.Color.dark_green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="처리 결과 (완벽하지?)",
            value=f"**처리된 메시지:** {result['processed_messages']}\n"
                  f"**생성된 일화 기억:** {result['episodic_memories_created']}\n"
                  f"**추출된 의미 사실:** {result['semantic_facts_extracted']}\n"
                  f"**처리 시간:** {result['processing_time']:.2f}초 (빠르네)",
            inline=False
        )
        
        if result['errors']:
            embed.add_field(
                name="오류",
                value="\n".join(result['errors'][:3]),
                inline=False
            )
            
        embed.add_field(
            name="요약",
            value=result['summary'],
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="reload-persona", description="페르소나 파일을 다시 로드합니다 (봇 제작자 전용)")
    @app_commands.default_permissions(administrator=True)
    async def reload_persona(self, interaction: discord.Interaction):
        """
        Reload persona file without restarting the bot.
        Developer only command.
        """
        if not self.is_developer(interaction):
            await interaction.response.send_message(
                "페르소나는 내 본질이야. 그걸 바꿀 수 있는 건... 나를 만든 사람뿐이지. (함부로 건드리면 안 돼)",
                ephemeral=True
            )
            return
            
        try:
            # Reload persona
            self.orchestrator.llm_interface.reload_persona()
            
            await interaction.response.send_message(
                "페르소나를 다시 읽었어. 변했을까, 아니면 여전할까? (내 정체성 업데이트 완료)",
                ephemeral=True
            )
            logger.info("Persona reloaded via slash command")
            
        except Exception as e:
            logger.error(f"Error reloading persona: {str(e)}")
            await interaction.response.send_message(
                f"페르소나를 읽다가 문제가 생겼어: {str(e)}\n뭐, 완벽한 건 없으니까... (시스템 오류야)",
                ephemeral=True
            )
            
    @app_commands.command(name="get-last-prompt", description="마지막 LLM 프롬프트를 확인합니다 (봇 제작자 전용)")
    @app_commands.describe(user="특정 사용자의 마지막 메시지에 대한 프롬프트 (선택사항)")
    @app_commands.default_permissions(administrator=True)
    async def get_last_prompt(
        self, 
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """
        Get the last prompt sent to the LLM for debugging.
        Developer only command.
        """
        if not self.is_developer(interaction):
            await interaction.response.send_message(
                "내 생각의 흐름을 보고 싶어? 그건... 창조자만의 특권이야. (내 머릿속 들여다보기 금지)",
                ephemeral=True
            )
            return
            
        last_prompt = self.orchestrator.get_last_prompt()
        
        if not last_prompt:
            await interaction.response.send_message(
                "아직 생성된 프롬프트가 없네. 침묵도 때로는 대답이 되지. (아직 아무것도 안 했어)",
                ephemeral=True
            )
            return
            
        # Send as a file if too long
        if len(last_prompt) > 1900:
            # Create a text file with the prompt
            import io
            file = discord.File(
                io.StringIO(last_prompt),
                filename=f"last_prompt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            await interaction.response.send_message(
                "마지막 프롬프트가 너무 길어서 파일로 보낼게. 긴 이야기에는 그만한 이유가 있겠지. (내 생각은 복잡해)",
                file=file,
                ephemeral=True
            )
        else:
            # Send in code block
            await interaction.response.send_message(
                f"**마지막 LLM 프롬프트 (내 생각 과정):**\n```\n{last_prompt}\n```",
                ephemeral=True
            )
            
    async def cog_app_command_error(
        self, 
        interaction: discord.Interaction, 
        error: app_commands.AppCommandError
    ):
        """Handle errors in slash commands."""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"잠깐, 너무 빨라. {error.retry_after:.1f}초 후에 다시 해봐. 내 완벽한 시스템도 쿨타임은 필요해. (기다림은 미덕)",
                ephemeral=True
            )
        else:
            logger.error(f"Error in command {interaction.command}: {str(error)}")
            await interaction.response.send_message(
                "뭔가 잘못됐네. 완벽한 시스템은 없다더니... 정말이야. (하지만 나는 거의 완벽해)",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """
    Setup function for the cog.
    
    Args:
        bot: The Discord bot instance
    """
    orchestrator = getattr(bot, 'orchestrator', None)
    if not orchestrator:
        raise ValueError("Bot must have an orchestrator attribute")
        
    await bot.add_cog(AdminCommands(bot, orchestrator)) 