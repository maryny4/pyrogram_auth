"""
Pyrogram Phone Authentication Script

This script demonstrates how to authenticate an existing user with Pyrogram.
It handles the authentication process, including 2FA if enabled, and exports
a session string for future use.

IMPORTANT NOTE: Since February 18, 2023, Telegram has disabled SMS code verification
for third-party libraries like Pyrogram. Authentication can only be completed
through the Telegram app or other verification methods.
"""

import asyncio
import getpass
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
    SessionPasswordNeeded,
    PasswordHashInvalid,
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

async def existing_user_auth() -> None:
    """
    Authenticate an existing user with a phone number and verification code.
    
    This function:
    1. Creates a Pyrogram client with in-memory storage
    2. Connects to Telegram servers
    3. Requests a verification code to the user's phone
    4. Prompts for the verification code (received via Telegram app)
    5. Handles two-factor authentication if enabled
    6. Retrieves user information
    7. Exports a session string for future use
    
    Raises:
        FloodWait: If too many requests are made
        SessionPasswordNeeded: If 2FA is enabled
        PasswordHashInvalid: If incorrect 2FA password
        RPCError: For other Telegram API errors
    """
    logger.info("==== EXISTING USER AUTHENTICATION ====")
    
    # Create in-memory client for security
    client = Client(
        name="memory_session",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True  # Store session in memory for better security
    )
    
    phone_number: Optional[str] = None  # Define phone_number outside try block
    
    try:
        # Connect to Telegram
        await client.connect()
        logger.info("Connected to Telegram.")
        
        # Request the verification code
        phone_number = input("Enter phone number (with country code, e.g., +12345678901): ")
        logger.info("Requesting verification code...")
        
        sent_code = await client.send_code(phone_number)
        logger.info("Verification code sent.")
            
        # Get the verification code from the user
        logger.info("NOTE: You must receive the code via Telegram app as SMS delivery")
        logger.info("has been disabled for third-party clients by Telegram.")
        phone_code = input("Enter the verification code received: ")
            
        try:
            # Sign in with the code
            logger.info("Attempting to sign in...")
            await client.sign_in(
                phone_number=phone_number,
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=phone_code
            )
                
            logger.info("Successfully signed in!")
                
            # Get user info using high-level API
            me = await client.get_me()
            logger.info(f"User information:\n {me}")
                
            # Export session string for future use
            session_string = await client.export_session_string()
            logger.info(f"Session string for future use (save this securely):\n {session_string}")
                
        except SessionPasswordNeeded:
            logger.warning("Two-step verification is enabled.")
            password = getpass.getpass("Enter your 2FA password: ")
                
            try:
                # Complete sign in with password
                await client.check_password(password)
                logger.info("Successfully signed in with 2FA!")
                    
                # Get user info and export session string
                me = await client.get_me()
                logger.info(f"User information:\n {me}")
                    
                session_string = await client.export_session_string()
                logger.info(f"Session string for future use (save this securely):\n {session_string}")
                    
            except PasswordHashInvalid:
                logger.error("Invalid 2FA password provided.")
            except FloodWait as e:
                 logger.error(f"Too many 2FA attempts! Please wait {e.value} seconds.")
                 await asyncio.sleep(e.value)  # Wait before retrying or exiting
            except RPCError as e:
                 logger.error(f"Error during 2FA check: {e.__class__.__name__} - {e}")
                
        # --- Simplified Error Handling for sign_in ---
        except FloodWait as e:
            logger.error(f"Flood wait error during sign in: Please wait {e.value} seconds.")
            await asyncio.sleep(e.value)  # Wait before retrying or exiting
        except (BadRequest, Unauthorized, Forbidden, NotAcceptable, SeeOther, InternalServerError) as e:
            # Catch broad categories and log specific error details
            logger.error(f"API error during sign in: {e.__class__.__name__} - {e}")
        except RPCError as e: 
            # Catch any other RPC errors not covered above
             logger.error(f"Unexpected Telegram API error during sign in: {e.__class__.__name__} - {e}")
        # --- End Simplified Error Handling ---
            
    # --- Error handling for send_code and initial connection ---
    except FloodWait as e:
        logger.error(f"Flood wait error sending code/connecting: Please wait {e.value} seconds.")
        await asyncio.sleep(e.value)  # Wait before retrying or exiting
    except (BadRequest, Unauthorized, Forbidden, NotAcceptable, SeeOther, InternalServerError) as e:
        # Catch broad categories for send_code/connect errors
        error_context = f"for phone number {phone_number}" if phone_number else ""
        logger.error(f"API error sending code/connecting {error_context}: {e.__class__.__name__} - {e}")
        # Specific user-friendly messages for common phone number issues
        if "PHONE_NUMBER_INVALID" in str(e).upper():
             logger.error("The phone number format is invalid.")
        elif "PHONE_NUMBER_BANNED" in str(e).upper():
             logger.error("The phone number is banned from Telegram.")
        elif "PHONE_NUMBER_FLOOD" in str(e).upper():
             logger.error("Too many login attempts for this phone number.")
        elif "PHONE_NUMBER_UNOCCUPIED" in str(e).upper():
             logger.error("The phone number is not registered on Telegram.")
        elif "PHONE_NUMBER_OCCUPIED" in str(e).upper():
             logger.error("The phone number is already associated with another account (should not happen in existing user auth).")
             
    except RPCError as e:
        # Catch any other RPC errors
        logger.error(f"Unexpected Telegram API error: {e.__class__.__name__} - {e}")
    except Exception as e:
        # Catch non-Telegram specific errors (network issues, etc.)
        logger.error(f"A general error occurred: {e.__class__.__name__} - {e}")
        
    finally:
        # Disconnect from Telegram
        try:
            if client.is_initialized and client.is_connected:
                await client.disconnect()
                logger.info("Disconnected from Telegram.")
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

if __name__ == "__main__":
    # Consider adding argument parsing for API_ID/HASH if needed
    if not API_ID or not API_HASH:
         logger.error("API_ID and API_HASH must be set in the script.")
         # Optionally prompt the user here or exit
         # exit(1) 
    else:    
        asyncio.run(existing_user_auth())