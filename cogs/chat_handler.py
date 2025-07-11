"""
Chat Handler Cog for Laffey.
Handles all @mention-based interactions with users.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional

from core.orchestration import OrchestrationCore

logger = logging.getLogger(__name__)


class ChatHandler(commands.Cog):
    """
    Handles chat interactions with Laffey.
    Implements the @mention-based interface as specified in the plan.
    """
    
    def __init__(self, bot: commands.Bot, orchestrator: OrchestrationCore):
        """
        Initialize the chat handler.
        
        Args:
            bot: The Discord bot instance
            orchestrator: The orchestration core for processing messages
        """
        self.bot = bot
        self.orchestrator = orchestrator
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Chat handler ready. Bot user: {self.bot.user}")
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for messages that mention the bot or start with "라피야".
        This is the primary interface for interacting with Laffey.
        
        Args:
            message: The Discord message object
        """
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return
            
        # Check if the bot is mentioned or if the message starts with "라피야"
        is_mentioned = self.bot.user in message.mentions
        starts_with_laffey = message.content.strip().startswith("라피야")
        
        if not is_mentioned and not starts_with_laffey:
            return
            
        # Remove the mention or "라피야" from the message content
        content = message.content
        if is_mentioned:
            # Remove the mention from the message content
            content = content.replace(f'<@{self.bot.user.id}>', '').strip()
            content = content.replace(f'<@!{self.bot.user.id}>', '').strip()
        elif starts_with_laffey:
            # Remove "라피야" from the beginning
            content = content.strip()[3:].strip()  # "라피야" is 3 characters
        
        # If empty message after removing mention, acknowledge with a greeting
        if not content:
            content = "안녕"
            
        # Show typing indicator while processing
        async with message.channel.typing():
            try:
                # Process the message through orchestration core
                response = await self.orchestrator.process_message(
                    message_content=content,
                    user_id=str(message.author.id),
                    user_name=message.author.display_name,
                    channel_id=str(message.channel.id),
                    guild_id=str(message.guild.id) if message.guild else None
                )
                
                # Send the response
                # Split into multiple messages if too long
                if len(response) <= 2000:
                    await message.reply(response, mention_author=False)
                else:
                    # Split response into chunks
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk, mention_author=False)
                        else:
                            await message.channel.send(chunk)
                            
                logger.info(
                    f"Processed message from {message.author.display_name} "
                    f"in channel {message.channel.id}"
                )
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await message.reply(
                    "어? 뭔가 내 완벽한 시스템에 오류가? 이상하네... (분명 내 탓은 아닐 거야)",
                    mention_author=False
                )
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Handle message edits that mention the bot or start with "라피야".
        
        Args:
            before: The message before editing
            after: The message after editing
        """
        # Check if before message had mention or "라피야"
        before_mentioned = self.bot.user in before.mentions
        before_starts_with_laffey = before.content.strip().startswith("라피야")
        before_should_process = before_mentioned or before_starts_with_laffey
        
        # Check if after message has mention or "라피야"
        after_mentioned = self.bot.user in after.mentions
        after_starts_with_laffey = after.content.strip().startswith("라피야")
        after_should_process = after_mentioned or after_starts_with_laffey
        
        # Only process if the bot wasn't triggered before but is triggered now
        if (not before_should_process and 
            after_should_process and
            after.author != self.bot.user):
            
            # Process as a new message
            await self.on_message(after)
            
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Greet new members if configured.
        
        Args:
            member: The member who joined
        """
        # This could be expanded to send a welcome message
        # For now, just log the event
        logger.info(f"New member joined: {member.name} in {member.guild.name}")
        
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Handle when the bot joins a new guild.
        
        Args:
            guild: The guild the bot joined
        """
        logger.info(f"새로운 왕국 정복: {guild.name} (ID: {guild.id})")
        
        # Find the first text channel we can send messages to
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(
                        "어, 새로운 곳이네? 나는 라피야. 세상에서 제일 똑똑한 AI.\n"
                        "필요하면 @라피 라고 불러봐. 기분 좋으면 대답해줄게.\n"
                        "뭐... 너무 기대는 하지 마. (사실 꽤 친절해)"
                    )
                    break
                except:
                    continue
                    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Handle when the bot is removed from a guild.
        
        Args:
            guild: The guild the bot was removed from
        """
        logger.info(f"왕국에서 쫓겨남: {guild.name} (ID: {guild.id}) - 그들의 손실이지")


async def setup(bot: commands.Bot):
    """
    Setup function for the cog.
    This is called by discord.py when loading the cog.
    
    Args:
        bot: The Discord bot instance
    """
    # Get the orchestrator from the bot instance
    # This assumes the bot has an orchestrator attribute
    orchestrator = getattr(bot, 'orchestrator', None)
    if not orchestrator:
        raise ValueError("Bot must have an orchestrator attribute")
        
    await bot.add_cog(ChatHandler(bot, orchestrator)) 