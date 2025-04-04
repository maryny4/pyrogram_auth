"""
Pyrogram Session String Authentication Script

This script demonstrates how to authenticate using a previously exported session string.
This is the recommended method for production applications as it avoids repeated
authentication processes.
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
    FloodWait,
    AuthKeyUnregistered, 
    AuthKeyInvalid,      
    AuthKeyDuplicated,   
    SessionExpired,      
    SessionRevoked,      
    UserDeactivated,     
    UserDeactivatedBan
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

async def session_string_auth() -> None:
    """
    Authenticate using a previously exported session string.
    
    This function:
    1. Prompts for a session string from a previous authentication
    2. Creates a Pyrogram client using the session string
    3. Connects to Telegram servers
    4. Retrieves user/bot information
    5. Identifies whether it's a bot or user account
    
    Raises:
        AuthKeyUnregistered: If the session has been invalidated
        AuthKeyInvalid: If the session is not valid
        SessionExpired: If the session has expired
        SessionRevoked: If the session has been revoked
        UserDeactivated: If the user account has been deactivated
        UserDeactivatedBan: If the user account has been banned
        FloodWait: If too many requests are made
        RPCError: For other Telegram API errors
    """
    logger.info("==== SESSION STRING AUTHENTICATION ====")
    
    # Get the session string from user input
    session_string = input("Enter your session string (from a previous export): ")
    
    if not session_string:
        logger.error("Session string cannot be empty.")
        return
    
    # Create client with session string (no need for file storage)
    client = Client(
        name="string_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string
        # no_updates=True # Consider adding if you don't need updates
    )
    
    try:
        # Start the client
        logger.info("Starting client with session string...")
        # Using client.connect() and client.disconnect() is often preferred
        # over start()/stop() for short-lived scripts or explicit control.
        await client.connect()
        logger.info("Client connected successfully!")
        
        # Get user/bot info
        logger.info("Getting account information...")
        me = await client.get_me()
        logger.info(f"Account info:\n{me}")
        
        # Determine if this is a bot or user account
        account_type = "bot" if me.is_bot else "user"
        logger.info(f"This is a {account_type} account.")
        
    # --- Specific Auth/Session Error Handling ---
    except (AuthKeyUnregistered, AuthKeyInvalid, SessionExpired, SessionRevoked) as e:
        logger.error(f"Session invalid ({e.__class__.__name__}): The session string is not valid or has expired/been revoked. Re-authentication required.")
    except AuthKeyDuplicated:
        logger.error("Session conflict: This session string is potentially being used elsewhere. Re-authentication is recommended.")
    except (UserDeactivated, UserDeactivatedBan) as e:
        logger.error(f"Account deactivated ({e.__class__.__name__}): This user account cannot be accessed.")
    # --- End Specific Auth/Session Error Handling ---
    
    except FloodWait as e:
        logger.error(f"Flood wait error: Please wait {e.value} seconds before trying again.")
        await asyncio.sleep(e.value)
        
    # --- Broader Pyrogram Error Categories --- 
    except SeeOther as e:
        logger.error(f"Redirect required: {e.__class__.__name__} - {e}")
    except Forbidden as e:
        logger.error(f"Forbidden operation: {e.__class__.__name__} - {e}")
    except NotAcceptable as e:
        logger.error(f"Not acceptable: {e.__class__.__name__} - {e}")
    except BadRequest as e:
        logger.error(f"Bad request: {e.__class__.__name__} - {e}")
    except InternalServerError as e:
        logger.error(f"Telegram server error: {e.__class__.__name__} - {e}. Please try again later.")
    except Unauthorized as e: # Catch other Unauthorized errors not handled above
         logger.error(f"Unauthorized error: {e.__class__.__name__} - {e}")
    except RPCError as e: # Catch any remaining RPC errors
        logger.error(f"Unhandled Telegram API error: {e.__class__.__name__} - {e}")
    # --- End Broader Pyrogram Error Categories ---
    
    except Exception as e:
        # Catch non-Telegram specific errors (network, config, etc.)
        logger.error(f"An unexpected general error occurred: {e.__class__.__name__} - {e}")
        
    finally:
        # Disconnect the client
        try:
            if client.is_initialized and client.is_connected:
                await client.disconnect()
                logger.info("Client disconnected.")
        except Exception as e:
            logger.error(f"Error disconnecting client: {e}")

if __name__ == "__main__":
    # Check for API_ID and API_HASH
    if not API_ID or not API_HASH:
         logger.error("API_ID and API_HASH must be set in the script.")
         # Optionally exit
         # exit(1)
    else:
        try:
            asyncio.run(session_string_auth())
        except KeyboardInterrupt:
            logger.info("Process interrupted by user.")
        except Exception as e:
             # Catch any unexpected errors during script execution
             logger.critical(f"Unhandled exception in main execution: {e.__class__.__name__} - {e}")