# Pyrogram Authentication Documentation

This document provides comprehensive information on authentication methods in Pyrogram,
including examples, expected responses, and important notes.

## IMPORTANT NOTE: 
Since February 18, 2023, Telegram has disabled SMS code verification for third-party libraries 
like Pyrogram and Telethon. Authentication can only be completed through official Telegram 
clients or other verification methods like the Telegram app code.

## Table of Contents
1. Existing User Authentication
2. Bot Authentication
3. Session String Authentication
4. Common Issues and Solutions
5. Response Examples
6. Security Considerations

## 1. Existing User Authentication

### Process Overview
1. Create a Client instance
2. Connect to Telegram
3. Request verification code
4. Enter the code (received via the Telegram app)
5. Handle 2FA if enabled
6. Get user information
7. Export session string

### Code Example

```python
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

# Create client
client = Client(
    "my_session",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True  # Store session in memory
)

# Connect to Telegram
await client.connect()

# Request verification code
sent_code = await client.send_code("+1234567890")
# sent_code contains phone_code_hash needed for signing in

# Sign in with code
try:
    user = await client.sign_in(
        phone_number="+1234567890",
        phone_code_hash=sent_code.phone_code_hash,
        phone_code="12345"  # Code from Telegram app
    )
except SessionPasswordNeeded:
    # 2FA is enabled
    user = await client.check_password("your_password")

# Export session for future use
session_string = await client.export_session_string()

# Disconnect
await client.disconnect()
```

### Expected Responses

#### `send_code()`:
```
SentCode(
    type=SentCodeType.APP,
    phone_code_hash="abcdefg123456789...",
    next_type=NextCodeType.CALL,
    timeout=120
)
```

#### `sign_in()`:
```
User(
    id=123456789,
    is_self=True,
    is_contact=True,
    is_mutual_contact=False,
    is_deleted=False,
    is_bot=False,
    is_verified=False,
    is_restricted=False,
    is_scam=False,
    is_fake=False,
    first_name="John",
    last_name="Doe",
    status=UserStatus.ONLINE,
    username="johndoe",
    language_code="en",
    dc_id=2,
    phone_number="+1234567890"
)
```

## 2. Bot Authentication

### Process Overview
1. Create a Client instance
2. Connect to Telegram
3. Sign in with a bot token
4. Get bot information
5. Export session string

### Code Example

```python
from pyrogram import Client

# Create client
client = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
)

# Connect to Telegram
await client.connect()

# Sign in with bot token
bot = await client.sign_in_bot("123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ")

# Get bot info
me = await client.get_me()

# Export session string
session_string = await client.export_session_string()

# Disconnect
await client.disconnect()
```

### Expected Responses

#### `sign_in_bot()`:
```
User(
    id=123456789,
    is_self=True,
    is_contact=False,
    is_mutual_contact=False,
    is_deleted=False,
    is_bot=True,
    is_verified=True,
    is_restricted=False,
    is_scam=False,
    is_fake=False,
    first_name="Bot Name",
    username="bot_username",
    language_code="en",
    dc_id=2
)
```

## 3. Session String Authentication

### Process Overview
1. Create a Client instance with a session string
2. Start the client
3. Get user/bot information
4. Stop the client

### Code Example

```python
from pyrogram import Client

# Create client with session string
client = Client(
    "string_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string="Your_Session_String"
)

# Start the client
await client.start()

# Get user/bot info
me = await client.get_me()

# Stop the client
await client.stop()
```

## 4. Common Issues and Solutions

### SMS Verification Limitation
**Issue**: Telegram no longer sends SMS verification codes to third-party applications.

**Solution**: 
- Receive the verification code via the official Telegram app
- Use the Telegram app to sign in first, then export the session string
- Use an MTProto proxy if necessary

### Two-Factor Authentication (2FA)
**Issue**: Account has 2FA enabled and requires a password.

**Solution**: Use `check_password()` to complete the sign-in process:
```python
user = await client.check_password("your_password")
```

### Session Expired
**Issue**: Previously saved sessions may expire.

**Solution**: Re-authenticate and create a new session.

### API ID and API Hash
**Issue**: Incorrect API credentials.

**Solution**: Double-check your API_ID and API_HASH from https://my.telegram.org/apps

## 5. Response Examples

### Raw API Responses

#### `functions.users.GetFullUser`:
```
UserFull(
    full_user=User(
        id=123456789,
        access_hash=987654321098765432,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        phone="1234567890",
        photo=UserProfilePhoto(...),
        status=UserStatus(...)
    ),
    chats=[],
    users=[...]
)
```

#### `functions.bots.GetBotInfo`:
```
BotInfo(
    bot_id=123456789,
    description="Bot description",
    about="About text",
    commands=[
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help")
    ]
)
```

## 6. Security Considerations

### Session Strings
- Session strings contain authorization data; keep them secure
- Don't share session strings with untrusted parties
- Session strings provide full access to the account

### 2FA Password
- Never store passwords in plain text
- Use getpass.getpass() to hide password input
- Consider secure credential management for production applications

### API Credentials
- Keep your API_ID and API_HASH private
- Don't commit them to public repositories
- Consider using environment variables or a secure configuration file

### Best Practices
- Use the minimal permissions required
- Log out inactive sessions regularly
- Use in_memory=True for temporary sessions
- Export and securely store session strings for long-term use
- Implement proper error handling for authentication failures
