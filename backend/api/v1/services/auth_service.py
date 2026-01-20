"""
API v1 Authentication Service
Handles user authentication, magic links, and session management
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from ..core.database import fetch_one, fetch_all, execute, execute_returning
from ..core.security import (
    hash_password, verify_password, generate_referral_code,
    generate_magic_link_token, generate_session_token, create_jwt_token,
    decode_jwt_token, check_brute_force, record_failed_attempt, clear_failed_attempts
)
from ..core.config import get_api_settings, ErrorCodes
from ..models import SignupResponse

settings = get_api_settings()


async def create_user(
    username: str,
    password: str,
    display_name: Optional[str] = None,
    referred_by_code: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create a new user account.
    Returns (success, data/error)
    """
    from ..core.database import get_db, serialize_doc, create_user_doc, generate_uuid
    
    username = username.lower().strip()
    
    # Use username as display_name if not provided
    if not display_name:
        display_name = username.title()
    
    # Check if username exists in MongoDB
    db = await get_db()
    existing = await db.users.find_one({"username": username})
    if existing:
        return False, {
            "message": "Username already exists",
            "error_code": ErrorCodes.USER_ALREADY_EXISTS
        }
    
    # Validate referral code if provided
    referrer_user_id = None
    if referred_by_code:
        referrer = await db.users.find_one(
            {"referral_code": referred_by_code.upper(), "is_active": True},
            {"user_id": 1, "username": 1}
        )
        referrer = serialize_doc(referrer)
        if not referrer:
            return False, {
                "message": "Invalid referral code",
                "error_code": ErrorCodes.INVALID_REFERRAL_CODE
            }
        referrer_user_id = referrer['user_id']
    
    # Generate unique referral code
    referral_code = generate_referral_code()
    while await db.users.find_one({"referral_code": referral_code}):
        referral_code = generate_referral_code()
    
    # Create user in MongoDB
    user_id = generate_uuid()
    password_hash = hash_password(password)
    
    user_doc = create_user_doc(
        user_id=user_id,
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        referral_code=referral_code,
        referred_by_code=referred_by_code.upper() if referred_by_code else None,
        referred_by_user_id=referrer_user_id
    )
    
    await db.users.insert_one(user_doc)
    
    # Log audit (compatibility layer will handle this)
    await log_audit(user_id, username, "user.signup", "user", user_id, {
        "referred_by": referred_by_code
    })
    
    # Emit USER_REGISTERED notification
    try:
        from ..core.notification_router import emit_event, EventType
        await emit_event(
            event_type=EventType.USER_REGISTERED,
            title="🆕 New Client Registered",
            message=f"A new client has joined the platform!\n\nUsername: @{username}\nDisplay Name: {display_name}" + (f"\nReferred by: {referred_by_code}" if referred_by_code else ""),
            reference_id=user_id,
            reference_type="user",
            user_id=user_id,
            username=username,
            display_name=display_name,
            extra_data={"referred_by": referred_by_code},
            requires_action=False
        )
        
        # If user was referred, also emit REFERRAL_JOINED
        if referrer_user_id:
            referrer = await db.users.find_one(
                {"user_id": referrer_user_id},
                {"username": 1, "display_name": 1}
            )
            referrer = serialize_doc(referrer)
            if referrer:
                await emit_event(
                    event_type=EventType.REFERRAL_JOINED,
                    title="👥 New Referral Joined",
                    message=f"A new user joined via referral!\n\nNew User: @{username}\nReferred By: @{referrer['username']}",
                    reference_id=user_id,
                    reference_type="referral",
                    user_id=referrer_user_id,
                    username=referrer['username'],
                    display_name=referrer['display_name'],
                    extra_data={"new_user": username, "referral_code": referred_by_code},
                    requires_action=False
                )
    except Exception as e:
        # Don't fail signup if notification fails
        import logging
        logging.getLogger(__name__).warning(f"Failed to send signup notification: {e}")
    
    return True, {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "referral_code": referral_code,
        "referred_by_code": referred_by_code.upper() if referred_by_code else None
    }


async def authenticate_user(username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Authenticate user with username and password.
    Returns (success, user_data/error)
    """
    username = username.lower().strip()
    
    # Check brute force lockout
    is_allowed, lockout_remaining = check_brute_force(username)
    if not is_allowed:
        return False, {
            "message": f"Account temporarily locked. Try again in {lockout_remaining} seconds",
            "error_code": ErrorCodes.ACCOUNT_LOCKED,
            "lockout_remaining": lockout_remaining
        }
    
    # Get user from MongoDB
    from ..core.database import get_db, serialize_doc
    db = await get_db()
    user = await db.users.find_one({"username": username})
    user = serialize_doc(user)
    
    if not user:
        record_failed_attempt(username)
        return False, {
            "message": "Invalid credentials",
            "error_code": ErrorCodes.INVALID_CREDENTIALS
        }
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        record_failed_attempt(username)
        return False, {
            "message": "Invalid credentials",
            "error_code": ErrorCodes.INVALID_CREDENTIALS
        }
    
    # Check if active
    if not user.get('is_active', True):
        return False, {
            "message": "Account is disabled",
            "error_code": ErrorCodes.ACCOUNT_LOCKED
        }
    
    # Clear failed attempts
    clear_failed_attempts(username)
    
    return True, {
        "user_id": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "referral_code": user['referral_code'],
        "role": user.get('role', 'user')
    }


async def create_magic_link(user_id: str, username: str) -> Dict[str, Any]:
    """
    Create a magic link for user authentication.
    Returns magic link data.
    """
    token = generate_magic_link_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expire_minutes)
    
    await execute('''
        INSERT INTO magic_links (user_id, token, expires_at)
        VALUES ($1, $2, $3)
    ''', user_id, token, expires_at)
    
    magic_link = f"{settings.magic_link_base_url}?token={token}"
    
    # Log audit
    await log_audit(user_id, username, "auth.magic_link_created", "magic_link", token[:16])
    
    return {
        "magic_link": magic_link,
        "token": token,
        "expires_in_seconds": settings.magic_link_expire_minutes * 60
    }


async def consume_magic_link(token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Consume a magic link and return session token.
    Returns (success, session_data/error)
    """
    # Find magic link
    magic_link = await fetch_one('''
        SELECT ml.*, u.username, u.display_name, u.referral_code
        FROM magic_links ml
        JOIN users u ON ml.user_id = u.user_id
        WHERE ml.token = $1 AND ml.consumed = FALSE
    ''', token)
    
    if not magic_link:
        return False, {
            "message": "Invalid or already used magic link",
            "error_code": ErrorCodes.INVALID_TOKEN
        }
    
    # Check expiration
    expires_at = magic_link['expires_at']
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return False, {
            "message": "Magic link has expired",
            "error_code": ErrorCodes.TOKEN_EXPIRED
        }
    
    # Mark as consumed
    await execute('''
        UPDATE magic_links SET consumed = TRUE, consumed_at = $1 WHERE token = $2
    ''', datetime.now(timezone.utc), token)
    
    # Get full user info including role
    user = await fetch_one(
        "SELECT role FROM users WHERE user_id = $1",
        magic_link['user_id']
    )
    
    # Create session
    access_token = create_jwt_token({
        "sub": magic_link['user_id'],
        "username": magic_link['username'],
        "type": "access"
    })
    
    session_expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    await execute('''
        INSERT INTO sessions (user_id, access_token, expires_at)
        VALUES ($1, $2, $3)
    ''', magic_link['user_id'], access_token, session_expires)
    
    # Log audit
    await log_audit(magic_link['user_id'], magic_link['username'], "auth.magic_link_consumed", "session", access_token[:16])
    
    return True, {
        "access_token": access_token,
        "expires_in_seconds": settings.access_token_expire_minutes * 60,
        "user": {
            "user_id": magic_link['user_id'],
            "username": magic_link['username'],
            "display_name": magic_link['display_name'],
            "referral_code": magic_link['referral_code'],
            "role": user.get('role', 'user') if user else 'user'
        }
    }


async def validate_token(token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate an access token.
    Returns (valid, user_data/error)
    """
    # Decode JWT
    payload = decode_jwt_token(token)
    if not payload:
        return False, {"message": "Invalid token", "error_code": ErrorCodes.INVALID_TOKEN}
    
    user_id = payload.get('sub')
    if not user_id:
        return False, {"message": "Invalid token", "error_code": ErrorCodes.INVALID_TOKEN}
    
    # Verify user exists and is active from MongoDB
    from ..core.database import get_db, serialize_doc
    db = await get_db()
    user = await db.users.find_one(
        {"user_id": user_id},
        {"user_id": 1, "username": 1, "display_name": 1, "referral_code": 1, "role": 1, "is_active": 1}
    )
    user = serialize_doc(user)
    
    if not user or not user.get('is_active', True):
        return False, {"message": "User not found or disabled", "error_code": ErrorCodes.USER_NOT_FOUND}
    
    # Note: Session tracking removed for MongoDB compatibility
    # JWT expiration is still validated
    
    return True, {
        "user_id": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "referral_code": user['referral_code'],
        "role": user.get('role', 'user'),
        "expires_at": datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    }


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    from ..core.database import get_db, serialize_doc
    db = await get_db()
    user = await db.users.find_one(
        {"username": username.lower()},
        {"user_id": 1, "username": 1, "display_name": 1, "referral_code": 1, "is_active": 1}
    )
    return serialize_doc(user)


async def log_audit(
    user_id: Optional[str],
    username: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log an audit event"""
    import json
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None, ip_address, user_agent)
