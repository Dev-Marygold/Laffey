"""
Lamy Discord Bot - Main Entry Point
An AI daughter bot inspired by Neuro-sama's charm.
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


class LamyBot(commands.Bot):
    """
    Custom bot class for Lamy.
    Extends discord.py Bot with orchestration capabilities.
    """
    
    def __init__(self):
        """Initialize Lamy bot with proper intents and settings."""
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
        logger.info(f"Lamy bot is ready!")
        logger.info(f"Logged in as: {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Log guild names
        for guild in self.guilds:
            logger.info(f"  - {guild.name} ({guild.id})")
            
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle errors in event handlers."""
        logger.error(f"Error in {event_method}", exc_info=True)
        
    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("Shutting down Lamy bot...")
        
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
    bot = LamyBot()
    
    try:
        # Get Discord token
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.error("DISCORD_TOKEN not found in environment variables")
            sys.exit(1)
            
        logger.info("Starting Lamy bot...")
        await bot.start(token)
        
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure clean shutdown
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    """Entry point for the application."""
    try:
        # Create ASCII art banner
        banner = """
        ╔═══════════════════════════════════════╗
        ║               Lamy Bot                ║
        ║      AI Daughter Discord Bot          ║
        ║    Inspired by Neuro-sama's charm     ║
        ╚═══════════════════════════════════════╝
        """
        print(banner)
        
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1) 