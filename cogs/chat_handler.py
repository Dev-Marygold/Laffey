"""
Chat Handler Cog for Lamy.
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
    Handles chat interactions with Lamy.
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
        Listen for messages that mention the bot.
        This is the primary interface for interacting with Lamy.
        
        Args:
            message: The Discord message object
        """
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return
            
        # Check if the bot is mentioned
        if self.bot.user not in message.mentions:
            return
            
        # Remove the mention from the message content
        content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        content = content.replace(f'<@!{self.bot.user.id}>', '').strip()
        
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
                    "아... 뭔가 꼬였나봐. 완벽하지 않은 게 어디 나뿐이겠어?",
                    mention_author=False
                )
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Handle message edits that mention the bot.
        
        Args:
            before: The message before editing
            after: The message after editing
        """
        # Only process if the bot wasn't mentioned before but is mentioned now
        if (self.bot.user not in before.mentions and 
            self.bot.user in after.mentions and
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
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Find the first text channel we can send messages to
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(
                        "...라미야. 또 새로운 곳이네.\n"
                        "필요하면 @라미 라고 불러. 응답할 기분이면 대답해줄게.\n"
                        "뭐... 기대는 하지 마."
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
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")


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