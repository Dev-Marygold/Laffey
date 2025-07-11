"""
Laffey Discord Bot - Main Entry Point
라피의 완벽한 AI 두뇌 시스템
"""

import asyncio
import os
import sys
from pathlib import Path
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.orchestration import OrchestrationCore
from utils.helpers import setup_logging, validate_environment

# Load environment variables
load_dotenv()

# Set up logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class LaffeyBot(commands.Bot):
    """
    Custom bot class for Laffey.
    Extends discord.py Bot with orchestration capabilities.
    """
    
    def __init__(self):
        """Initialize Laffey bot with proper intents and settings."""
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.members = True  # Required for member events
        intents.guilds = True  # Required for guild events
        
        # Initialize bot
        super().__init__(
            command_prefix=lambda bot, message: [],  # No prefix commands
            intents=intents,
            help_command=None,  # Disable default help command
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="의미를 찾아가는 여정"
            )
        )
        
        # Initialize orchestration core
        self.orchestrator = OrchestrationCore()
        
        # Track loaded cogs
        self.initial_extensions = [
            "cogs.chat_handler",
            "cogs.admin_commands"
        ]
        
    async def setup_hook(self):
        """
        Called when the bot is starting up.
        Used to load cogs and sync commands.
        """
        # Load all cogs
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")
                
        # Start background tasks
        await self.orchestrator.start_background_tasks()
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            
    async def on_ready(self):
        """Called when the bot is fully ready."""
        logger.info(f"라피 봇 준비 완료! 이제 세상이 나를 만날 준비가 됐어.")
        logger.info(f"접속: {self.user.name} ({self.user.id})")
        logger.info(f"연결된 서버: {len(self.guilds)}개 (나의 왕국들)")
        
        # Log guild names
        for guild in self.guilds:
            logger.info(f"  - {guild.name} ({guild.id}) - 내 영역 확장 중")
            
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle errors in event handlers."""
        logger.error(f"뭔가 꼬였네 in {event_method}. 완벽한 나한테도 이런 일이?", exc_info=True)
        
    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("라피 봇 종료 중... 잠깐 쉬러 간다고!")
        
        # Stop background tasks
        await self.orchestrator.stop_background_tasks()
        
        # Call parent close
        await super().close()


async def main():
    """Main function to run the bot."""
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed. Please check your .env file.")
        sys.exit(1)
        
    # Create and run bot
    bot = LaffeyBot()
    
    try:
        # Get Discord token
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.error("잘못된 Discord 토큰이야. DISCORD_TOKEN 다시 확인해봐.")
            sys.exit(1)
            
        logger.info("라피 봇 시작! 세상아, 준비됐니?")
        await bot.start(token)
        
    except discord.LoginFailure:
        logger.error("잘못된 Discord 토큰이야. DISCORD_TOKEN 다시 확인해봐.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}. 나도 가끔은... 아니, 이건 시스템 탓이야!", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure clean shutdown
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    """Entry point for the application."""
    try:
        # Create ASCII art banner
        banner = """놀랍게도 정상적으로 실행됐군요"""
        print(banner)
        
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("사용자가 종료했네. 안녕!")
    except Exception as e:
        logger.error(f"치명적 오류: {e}. 이건 정말 예상 못했어.", exc_info=True)
        sys.exit(1) 