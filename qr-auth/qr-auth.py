"""
Pyrogram QR Authentication Script

This script demonstrates how to authenticate using Telegram's QR code method with Pyrogram.
It generates a QR code that can be scanned with the Telegram mobile app to authenticate
a session without entering a phone number or verification code.

This authentication method allows you to create a session file or session string
that can be used for future logins without re-authentication.

Usage:
1. Run the script
2. Select a Data Center (DC) or use the nearest one
3. Scan the QR code using the Telegram mobile app:
   Settings > Devices > Link Desktop Device
4. A session string will be generated for future use

Note: The script will generate up to 3 QR codes per session, with each code valid for 30 seconds.
"""

import asyncio
import logging
import getpass
from base64 import urlsafe_b64encode
from typing import Optional, Dict, Any

from pyrogram import Client, raw, errors
from pyrogram.session import Session, Auth
from pyrogram.handlers import RawUpdateHandler
from qrcode import QRCode  # Make sure qrcode package is installed

# --- Basic Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# --- End Logging Configuration ---

# Configuration (replace with your own values)
API_ID = 0  # Replace with your API ID
API_HASH = ""  # Replace with your API Hash

# Production Data Center Information
DC_INFO = {
    1: {"location": "Miami FL, USA", "ipv4": "149.154.175.53", "ipv6": "2001:b28:f23d:f001::a"},
    2: {"location": "Amsterdam, NL", "ipv4": "149.154.167.51", "ipv6": "2001:67c:4e8:f002::a"},
    3: {"location": "Miami FL, USA (alias)", "ipv4": "149.154.175.100", "ipv6": "2001:b28:f23d:f003::a"},
    4: {"location": "Amsterdam, NL", "ipv4": "149.154.167.91", "ipv6": "2001:67c:4e8:f004::a"},
    5: {"location": "Singapore, SG", "ipv4": "91.108.56.130", "ipv6": "2001:b28:f23f:f005::a"}
}

# Global variables
SESSION_CREATED = asyncio.Event()
DC_MIGRATED = asyncio.Event()  # Signal for DC migration
MAX_QR_CODES = 3  # Maximum number of QR codes to generate per DC
QR_TIMEOUT = 30  # QR code timeout in seconds
nearest_dc = None  # Will store the nearest or selected DC ID

def print_dc_info() -> None:
    """
    Print information about available Telegram Data Centers.
    """
    print("\nAvailable Telegram Data Centers:")
    print("-" * 60)
    print(f"{'ID':<4}{'Location':<25}{'IPv4':<20}{'IPv6'}")
    print("-" * 60)
    
    for dc_id, info in DC_INFO.items():
        print(f"{dc_id:<4}{info['location']:<25}{info['ipv4']:<20}{info['ipv6']}")
    print()

async def generate_qr(token: bytes) -> None:
    """
    Generate a QR code from a token and print it in ASCII format.
    
    Args:
        token (bytes): The token to encode in the QR code.
    """
    token_b64 = urlsafe_b64encode(token).decode("utf8")
    login_url = f"tg://login?token={token_b64}"
    
    qr = QRCode()
    qr.clear()
    qr.add_data(login_url)
    qr.print_ascii()

async def check_session(client: Client, dc_id: int) -> bool:
    """
    Create or recreate a session for the specified Data Center.
    
    Args:
        client (Client): The Pyrogram client instance.
        dc_id (int): The ID of the data center to use.
        
    Returns:
        bool: True if the session was successfully created, False otherwise.
    """
    try:
        # Stop the current session if it exists
        if hasattr(client, 'session') and client.is_connected:
            await client.session.stop()
        
        # Update the DC ID in storage
        await client.storage.dc_id(dc_id)
        
        # Create new auth key
        auth_key = await Auth(
            client, 
            await client.storage.dc_id(),
            await client.storage.test_mode()
        ).create()
        
        # Store the auth key
        await client.storage.auth_key(auth_key)
        
        # Create a new session
        client.session = Session(
            client, 
            await client.storage.dc_id(),
            await client.storage.auth_key(), 
            await client.storage.test_mode()
        )
        
        # Start the new session
        session_started = await client.session.start()
        return session_started
    except Exception as e:
        logger.error(f"Error in check_session: {e}")
        return False

async def handle_2fa(client: Client) -> bool:
    """
    Handle two-factor authentication if needed.
    
    Args:
        client (Client): The Pyrogram client instance.
        
    Returns:
        bool: True if 2FA authentication was successful, False otherwise.
    """
    try:
        logger.info("Two-factor authentication required")
        password = getpass.getpass("Enter your 2FA password: ")
        
        # Check the password
        await client.check_password(password)
        logger.info("2FA authentication successful")
        return True
    except errors.PasswordHashInvalid:
        logger.error("Invalid 2FA password")
        return False
    except errors.FloodWait as e:
        logger.error(f"Too many attempts. Please wait {e.value} seconds")
        return False
    except Exception as e:
        logger.error(f"Error during 2FA: {e}")
        return False

async def raw_update_handler(client: Client, update: Any, users: Dict, chats: Dict) -> None:
    """
    Handle raw updates from Telegram for QR authentication.
    
    Args:
        client (Client): The Pyrogram client.
        update (Any): The update object from Telegram.
        users (Dict): Dictionary of users related to the update.
        chats (Dict): Dictionary of chats related to the update.
    """
    global nearest_dc
    
    # Check if we need to switch DC
    if nearest_dc is not None:
        current_dc = await client.storage.dc_id()
        if isinstance(update, raw.types.auth.LoginToken) and nearest_dc != current_dc:
            logger.info(f"DC mismatch detected. Switching from DC {current_dc} to DC {nearest_dc}")
            await check_session(client, dc_id=nearest_dc)
    
    # Handle login token updates (when QR code is scanned)
    if isinstance(update, raw.types.UpdateLoginToken):
        logger.info("QR code was scanned! Processing login...")
        
        try:
            # Export login token to complete the authentication
            result = await client.invoke(
                raw.functions.auth.ExportLoginToken(
                    api_id=API_ID, api_hash=API_HASH, except_ids=[]
                )
            )
            
            # Handle successful authentication
            if isinstance(result, raw.types.auth.LoginTokenSuccess):
                logger.info("Authentication successful!")
                
                # Get user information
                try:
                    me = await client.get_me()
                    logger.info(f"User information:\n{me}")
                    
                    # Export session string
                    session_string = await client.export_session_string()
                    print(f"\nSession string for future use (save this securely):\n{session_string}\n")
                    
                except Exception as e:
                    logger.error(f"Error getting user info: {e}")
                
                # Set the session created event
                SESSION_CREATED.set()
            
            # Handle DC migration
            elif isinstance(result, raw.types.auth.LoginTokenMigrateTo):
                dc_id = result.dc_id
                logger.info(f"Need to migrate to DC {dc_id}")
                
                # Switch to the specified DC
                if await check_session(client, dc_id=dc_id):
                    logger.info(f"Session switched to DC {dc_id}")
                else:
                    logger.error(f"Failed to switch to DC {dc_id}")
                    # We'll continue anyway
                
                # Signal that a DC migration occurred but DON'T generate QR code here
                # Let the main loop in create_qrcodes handle it
                DC_MIGRATED.set()
                
                print(f"\nMigrating to DC {dc_id}. A new QR code will be generated soon...")
            
        except errors.SessionPasswordNeeded:
            # Handle 2FA
            if await handle_2fa(client):
                # Try again after successful 2FA
                try:
                    result = await client.invoke(
                        raw.functions.auth.ExportLoginToken(
                            api_id=API_ID, api_hash=API_HASH, except_ids=[]
                        )
                    )
                    
                    if isinstance(result, raw.types.auth.LoginTokenSuccess):
                        logger.info("Login successful after 2FA!")
                        
                        try:
                            me = await client.get_me()
                            logger.info(f"User information:\n{me}")
                            
                            # Export session string
                            session_string = await client.export_session_string()
                            print(f"\nSession string for future use (save this securely):\n{session_string}\n")
                        except Exception as e:
                            logger.error(f"Error getting user info after 2FA: {e}")
                        
                        SESSION_CREATED.set()
                except Exception as e:
                    logger.error(f"Error after 2FA: {e}")
            
        except Exception as e:
            logger.error(f"Error handling login token update: {e}")

async def create_qrcodes(client: Client) -> None:
    """
    Generate QR codes for authentication in a loop until successful or max attempts reached.
    
    Args:
        client (Client): The Pyrogram client.
    """
    qr_counter = 0
    dc_migrated_flag = False
    
    while not SESSION_CREATED.is_set():
        # Reset counter and wait briefly if DC migration occurred
        if DC_MIGRATED.is_set():
            qr_counter = 0
            dc_migrated_flag = True
            logger.info("DC migration detected, resetting QR code counter")
            
            # Wait briefly for session to stabilize after migration
            await asyncio.sleep(2)
            
            DC_MIGRATED.clear()
        
        qr_counter += 1
        
        # Check if we've exceeded max QR codes for this DC
        if qr_counter > MAX_QR_CODES:
            print(f"\nMaximum number of QR codes ({MAX_QR_CODES}) for this DC generated without success.")
            
            # Wait for potential DC migration
            try:
                await asyncio.wait_for(DC_MIGRATED.wait(), 10)
                if DC_MIGRATED.is_set():
                    # DC migration occurred, we'll start new QR codes
                    continue
                else:
                    # No migration and max QR codes reached
                    print("Please try again later.")
                    return
            except asyncio.TimeoutError:
                # No migration happened, exit
                print("Please try again later.")
                return
            
        # Show appropriate message based on context
        if dc_migrated_flag:
            print("\nHere's a new QR code after DC migration. Please scan it:")
            dc_migrated_flag = False
        elif qr_counter == 1:
            print('\nScan this QR code in the Telegram app:')
            print('Settings > Devices > Link Desktop Device\n')
        else:
            print(f"\nQR code expired. Generating new QR code ({qr_counter}/{MAX_QR_CODES}):\n")
            
        try:
            # Request a login token
            result = await client.invoke(
                raw.functions.auth.ExportLoginToken(
                    api_id=API_ID, api_hash=API_HASH, except_ids=[]
                )
            )
            
            # Generate QR code if we received a token
            if isinstance(result, raw.types.auth.LoginToken):
                logger.info(f"Generated QR code #{qr_counter}/{MAX_QR_CODES} (expires in {QR_TIMEOUT} seconds)")
                await generate_qr(result.token)
                
                # Wait for the QR code to be scanned, to expire, or for DC migration
                while True:
                    # Create a future that returns when any of these events occur
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(SESSION_CREATED.wait()),
                            asyncio.create_task(asyncio.sleep(QR_TIMEOUT)),
                            asyncio.create_task(DC_MIGRATED.wait())
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                    
                    # Check which event completed
                    if SESSION_CREATED.is_set():
                        return
                    elif DC_MIGRATED.is_set():
                        logger.info("DC migration occurred, will generate new QR codes")
                        break
                    else:
                        logger.info(f"QR code #{qr_counter} expired after {QR_TIMEOUT} seconds")
                        break
            else:
                logger.warning(f"Unexpected response when generating QR code: {type(result).__name__}")
                await asyncio.sleep(3)
        except errors.FloodWait as e:
            logger.warning(f"Rate limited. Waiting {e.value} seconds")
            await asyncio.sleep(e.value)
        except errors.RPCError as e:
            logger.error(f"Telegram API error generating QR code: {type(e).__name__} - {e}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Unexpected error generating QR code: {type(e).__name__} - {e}")
            await asyncio.sleep(3)

async def qr_auth() -> None:
    """
    Authenticate using Telegram's QR code method.
    
    This function:
    - Prompts for DC selection
    - Connects to Telegram
    - Determines the appropriate Data Center
    - Generates QR codes for authentication
    - Handles the authentication process
    - Creates a session string for future use
    """
    global nearest_dc
    logger.info("==== QR CODE AUTHENTICATION =====")
    
    # Print available DCs
    print_dc_info()
    
    # Ask for DC selection
    dc_choice = input("Select DC number (1-5) or press Enter for nearest DC: ")
    selected_dc = None
    
    if dc_choice and dc_choice.isdigit():
        dc_num = int(dc_choice)
        if 1 <= dc_num <= 5:
            selected_dc = dc_num
            info = DC_INFO[selected_dc]
            logger.info(f"Selected DC{selected_dc}: {info['location']} ({info['ipv4']})")
        else:
            logger.warning("Invalid DC number. Using nearest DC.")
    
    # Create Pyrogram client with in-memory storage
    client = Client(
        name="qr_auth_session",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    
    nearest_dc = None
    
    try:
        # Connect to Telegram
        logger.info("Connecting to Telegram servers...")
        await client.connect()
        logger.info("Connected successfully")
        
        # Determine which DC to use
        if selected_dc:
            nearest_dc = selected_dc
            logger.info(f"Using user-selected DC: {nearest_dc}")
        else:
            # Get the nearest DC if none was specified
            try:
                nearest_dc_info = await client.invoke(raw.functions.help.GetNearestDc())
                nearest_dc = nearest_dc_info.nearest_dc
                
                # Print info about the nearest DC
                if nearest_dc in DC_INFO:
                    info = DC_INFO[nearest_dc]
                    logger.info(f"Using nearest DC{nearest_dc}: {info['location']} ({info['ipv4']})")
            except Exception as e:
                logger.error(f"Error getting nearest DC: {e}")
                nearest_dc = 2  # Default to DC 2 if we can't determine the nearest
                logger.info(f"Defaulting to DC{nearest_dc}")
        
        # Create a session with the selected/nearest DC
        if nearest_dc:
            logger.info(f"Setting up session with DC {nearest_dc}")
            
            if not await check_session(client, nearest_dc):
                logger.warning(f"Failed to set up session with DC {nearest_dc}")
                # Continue anyway - let's try to generate QR codes
        
        # Set up raw update handler
        client.add_handler(
            RawUpdateHandler(raw_update_handler)
        )
        
        # Start the update dispatcher
        await client.dispatcher.start()
        
        # Start generating QR codes
        logger.info(f"Starting QR code generation (max {MAX_QR_CODES} codes, {QR_TIMEOUT} seconds each)")
        await create_qrcodes(client)
        
        # Wait until the session is created or until all QR codes have expired
        if SESSION_CREATED.is_set():
            logger.info("Authentication completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean up
        try:
            if hasattr(client, 'dispatcher'):
                await client.dispatcher.stop()
        except Exception as e:
            logger.error(f"Error stopping dispatcher: {e}")
        
        try:
            await client.disconnect()
            logger.info("Disconnected from Telegram")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

if __name__ == "__main__":
    # Check for API_ID and API_HASH
    if not API_ID or not API_HASH:
        logger.error("API_ID and API_HASH must be set in the script.")
        print("Please set your API_ID and API_HASH in the script.")
        exit(1)
    
    try:
        asyncio.run(qr_auth())
    except KeyboardInterrupt:
        print("\nExiting...")