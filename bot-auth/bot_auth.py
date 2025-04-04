"""
Pyrogram Bot Authentication Script

This script demonstrates how to authenticate a bot with Pyrogram.
It signs in with a bot token from BotFather and exports a session string for future use.

This authentication method is for bots only and requires a bot token from BotFather.
"""

import asyncio
import logging
from typing import Optional

from pyrogram import Client
from pyrogram.errors import (
    # Base error
    RPCError,
    
    # Error categories
    BadRequest,
    Unauthorized,
    Forbidden,
    NotAcceptable,
    Flood,
    InternalServerError,
    SeeOther,
    
    # Specific errors for special handling
    AccessTokenInvalid, 
    AccessTokenExpired,
    FloodWait,
)

# --- Basic Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# --- End Logging Configuration ---


# Configuration (replace with your own values)
API_ID: int = 0  # Replace with your API ID
API_HASH: str = ""  # Replace with your API Hash

async def bot_auth() -> None:
    """
    Authenticate a bot using its token from BotFather.
    
    This function:
    1. Creates a Pyrogram client with in-memory storage
    2. Connects to Telegram servers
    3. Signs in with the bot token
    4. Retrieves bot information
    5. Exports a session string for future use
    
    Raises:
        AccessTokenInvalid: If the bot token is invalid
        AccessTokenExpired: If the bot token has expired
        FloodWait: If too many requests are made
        RPCError: For other Telegram API errors
    """
    logger.info("==== BOT AUTHENTICATION ====")
    
    # Create client with in-memory storage for security
    client = Client(
        name="bot_session",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True  # Store session in memory for better security
    )
    
    bot_token: Optional[str] = None  # Define bot_token outside try block
    
    try:
        # Connect to Telegram
        logger.info("Connecting to Telegram...")
        await client.connect()
        logger.info("Connected to Telegram.")
        
        # Get bot token from user input
        bot_token = input("Enter bot token (from BotFather, e.g., 123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ): ")
        
        try:
            # Sign in as bot using the provided token
            logger.info("Attempting to sign in as bot...")
            await client.sign_in_bot(bot_token)  # No need to store 'bot' typically
            logger.info("Successfully signed in as bot!")
            
            # Get bot info using high-level API
            logger.info("Getting bot info...")
            me = await client.get_me()
            logger.info(f"Bot information:\n{me}")
            
            # Export session string for future authentication
            session_string = await client.export_session_string()
            logger.info(f"Bot session string (for future use):\n{session_string}")
            
        # --- Simplified Error Handling for sign_in_bot ---
        except AccessTokenInvalid:
            logger.error("The bot token provided is invalid. Please check it and try again.")
        except AccessTokenExpired:
             logger.error("The bot token has expired. Please obtain a new token from BotFather.")
        except FloodWait as e:
            logger.error(f"Flood wait error during bot sign in: Please wait {e.value} seconds.")
            await asyncio.sleep(e.value)  # Wait before retrying or exiting
        except (BadRequest, Unauthorized, Forbidden, NotAcceptable, SeeOther, InternalServerError) as e:
            # Catch broad categories and log specific error details
            logger.error(f"API error during bot sign in: {e.__class__.__name__} - {e}")
            
            # Check for common Unauthorized reasons if needed
            if isinstance(e, Unauthorized):
                 if "AUTH_KEY" in str(e).upper():
                     logger.warning("Auth key issue detected. If errors persist, try removing the session file (if any) and retrying.")
                 elif "SESSION" in str(e).upper():
                     logger.warning("Session issue detected (revoked/expired). A new session string will be generated if login succeeds.")
        except RPCError as e: 
            # Catch any other RPC errors not covered above
             logger.error(f"Unexpected Telegram API error during bot sign in: {e.__class__.__name__} - {e}")
        except Exception as e:
             # Catch non-Telegram specific errors
             logger.error(f"A general error occurred during bot sign in steps: {e.__class__.__name__} - {e}")
        # --- End Simplified Error Handling ---
            
    # --- Error handling for connect ---
    except RPCError as e:
        # Catch any RPC errors during initial connection
        logger.error(f"Telegram API error during connection: {e.__class__.__name__} - {e}")
    except Exception as e:
        # Catch non-Telegram specific errors (network issues, etc.) during connection
        logger.error(f"A general error occurred during connection: {e.__class__.__name__} - {e}")
        
    finally:
        # Disconnect from Telegram
        try:
            if client.is_initialized and client.is_connected:
                await client.disconnect()
                logger.info("Disconnected from Telegram.")
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

if __name__ == "__main__":
    # Check for API_ID and API_HASH
    if not API_ID or not API_HASH:
         logger.error("API_ID and API_HASH must be set in the script.")
         # Optionally exit here:
         # exit(1)
    else:
        try:
            asyncio.run(bot_auth())
        except KeyboardInterrupt:
            logger.info("Process interrupted by user.")
        except Exception as e:
             # Catch any unexpected errors during script execution
             logger.critical(f"Unhandled exception in main execution: {e.__class__.__name__} - {e}")