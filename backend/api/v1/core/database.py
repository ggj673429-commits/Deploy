"""
API v1 Database Module - UNIFIED DATABASE LAYER (MongoDB)
MongoDB connection and collection management
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import uuid

from .config import get_api_settings

logger = logging.getLogger(__name__)
settings = get_api_settings()

# MongoDB client and database
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def get_db() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance"""
    global _db
    if _db is None:
        raise Exception("Database not connected. Call init_api_v1_db() first.")
    return _db


async def init_api_v1_db():
    """Initialize the MongoDB connection and create indexes"""
    global _client, _db
    
    logger.info("Initializing MongoDB connection...")
    logger.info(f"Database: {settings.db_name}")
    
    # Create MongoDB client
    _client = AsyncIOMotorClient(settings.mongo_url)
    _db = _client[settings.db_name]
    
    # Test connection
    try:
        await _client.admin.command('ping')
        logger.info("✅ MongoDB connection successful")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise
    
    # Create indexes for all collections
    await _create_indexes()
    
    logger.info("✅ Database initialized successfully")


async def _create_indexes():
    """Create indexes for all collections"""
    db = await get_db()
    
    try:
        # Users collection indexes
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("username", unique=True)
        await db.users.create_index("referral_code", unique=True)
        await db.users.create_index("referred_by_code")
        await db.users.create_index("email")
        await db.users.create_index("role")
        await db.users.create_index("created_at")
        
        # User identities indexes
        await db.user_identities.create_index("identity_id", unique=True)
        await db.user_identities.create_index([("user_id", 1), ("provider", 1), ("provider_user_id", 1)], unique=True)
        await db.user_identities.create_index("provider")
        
        # Sessions indexes
        await db.sessions.create_index("session_id", unique=True)
        await db.sessions.create_index("user_id")
        await db.sessions.create_index("expires_at")
        
        # Orders indexes
        await db.orders.create_index("order_id", unique=True)
        await db.orders.create_index("user_id")
        await db.orders.create_index("status")
        await db.orders.create_index("order_type")
        await db.orders.create_index("created_at")
        
        # Transactions indexes
        await db.transactions.create_index("transaction_id", unique=True)
        await db.transactions.create_index("user_id")
        await db.transactions.create_index("order_id")
        await db.transactions.create_index("transaction_type")
        await db.transactions.create_index("created_at")
        
        # Referrals indexes
        await db.referrals.create_index("referral_id", unique=True)
        await db.referrals.create_index("referrer_user_id")
        await db.referrals.create_index("referee_user_id", unique=True)
        await db.referrals.create_index("referral_code")
        
        # Referral earnings indexes
        await db.referral_earnings.create_index("earning_id", unique=True)
        await db.referral_earnings.create_index("referrer_user_id")
        await db.referral_earnings.create_index("referee_user_id")
        await db.referral_earnings.create_index("trigger_type")
        await db.referral_earnings.create_index("created_at")
        
        # Promo codes indexes
        await db.promo_codes.create_index("promo_id", unique=True)
        await db.promo_codes.create_index("code", unique=True)
        await db.promo_codes.create_index("is_active")
        await db.promo_codes.create_index("expires_at")
        
        # Promo redemptions indexes
        await db.promo_redemptions.create_index("redemption_id", unique=True)
        await db.promo_redemptions.create_index("user_id")
        await db.promo_redemptions.create_index("promo_id")
        await db.promo_redemptions.create_index([("user_id", 1), ("promo_id", 1)], unique=True)
        
        # Game accounts indexes
        await db.game_accounts.create_index("game_account_id", unique=True)
        await db.game_accounts.create_index("user_id", unique=True)
        await db.game_accounts.create_index("game_username")
        
        # Game operations indexes
        await db.game_operations.create_index("operation_id", unique=True)
        await db.game_operations.create_index("user_id")
        await db.game_operations.create_index("game_account_id")
        await db.game_operations.create_index("operation_type")
        await db.game_operations.create_index("status")
        await db.game_operations.create_index("created_at")
        
        # Wagering history indexes
        await db.wagering_history.create_index("wager_id", unique=True)
        await db.wagering_history.create_index("user_id")
        await db.wagering_history.create_index("game_account_id")
        await db.wagering_history.create_index("created_at")
        
        # Admin balance adjustments indexes
        await db.admin_balance_adjustments.create_index("adjustment_id", unique=True)
        await db.admin_balance_adjustments.create_index("user_id")
        await db.admin_balance_adjustments.create_index("admin_user_id")
        await db.admin_balance_adjustments.create_index("created_at")
        
        # Promotions indexes
        await db.promotions.create_index("promotion_id", unique=True)
        await db.promotions.create_index("is_active")
        await db.promotions.create_index("promotion_type")
        await db.promotions.create_index("created_at")
        
        # Telegram webhooks indexes
        await db.telegram_webhooks.create_index("webhook_id", unique=True)
        await db.telegram_webhooks.create_index("update_id", unique=True)
        await db.telegram_webhooks.create_index("chat_id")
        await db.telegram_webhooks.create_index("created_at")
        
        # Referral tiers indexes
        await db.referral_tiers.create_index("tier_id", unique=True)
        await db.referral_tiers.create_index("tier_level", unique=True)
        
        logger.info("✅ All indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        # Don't raise - indexes are optional for functionality


async def close_api_v1_db():
    """Close the database connection"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("Database connection closed")


# ==================== Helper Functions ====================

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def get_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


async def user_exists(user_id: str) -> bool:
    """Check if user exists"""
    db = await get_db()
    user = await db.users.find_one({"user_id": user_id})
    return user is not None


async def username_exists(username: str) -> bool:
    """Check if username exists"""
    db = await get_db()
    user = await db.users.find_one({"username": username})
    return user is not None


async def referral_code_exists(referral_code: str) -> bool:
    """Check if referral code exists"""
    db = await get_db()
    user = await db.users.find_one({"referral_code": referral_code})
    return user is not None


# ==================== MongoDB Query Helpers ====================

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    
    # Remove MongoDB _id field
    if "_id" in doc:
        del doc["_id"]
    
    # Convert datetime objects to ISO strings
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    
    return doc


def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert list of MongoDB documents to JSON-serializable dicts"""
    return [serialize_doc(doc) for doc in docs if doc is not None]


# ==================== Default Document Structures ====================

def create_user_doc(
    user_id: str,
    username: str,
    password_hash: str,
    display_name: str,
    referral_code: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    referred_by_code: Optional[str] = None,
    referred_by_user_id: Optional[str] = None,
    role: str = "user"
) -> Dict[str, Any]:
    """Create a user document"""
    now = get_timestamp()
    return {
        "user_id": user_id,
        "username": username,
        "password_hash": password_hash,
        "display_name": display_name,
        "email": email,
        "phone": phone,
        "referral_code": referral_code,
        "referred_by_code": referred_by_code,
        "referred_by_user_id": referred_by_user_id,
        "role": role,
        "is_active": True,
        "is_verified": False,
        "bonus_percentage": 0.0,
        "signup_bonus_claimed": False,
        "deposit_count": 0,
        "total_deposited": 0.0,
        "total_withdrawn": 0.0,
        "real_balance": 0.0,
        "bonus_balance": 0.0,
        "play_credits": 0.0,
        "cash_balance": 0.0,
        "withdraw_locked": False,
        "deposit_locked": False,
        "is_suspicious": False,
        "manual_approval_only": False,
        "no_bonus": False,
        "visibility_level": "full",
        "last_ip": None,
        "created_at": now,
        "updated_at": now
    }


def create_order_doc(
    order_id: str,
    user_id: str,
    order_type: str,
    amount: float,
    status: str = "pending",
    **kwargs
) -> Dict[str, Any]:
    """Create an order document"""
    now = get_timestamp()
    return {
        "order_id": order_id,
        "user_id": user_id,
        "order_type": order_type,
        "amount": amount,
        "status": status,
        "created_at": now,
        "updated_at": now,
        **kwargs
    }


def create_transaction_doc(
    transaction_id: str,
    user_id: str,
    transaction_type: str,
    amount: float,
    order_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a transaction document"""
    now = get_timestamp()
    return {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "transaction_type": transaction_type,
        "amount": amount,
        "order_id": order_id,
        "created_at": now,
        **kwargs
    }


# Export main functions
__all__ = [
    "get_db",
    "init_api_v1_db",
    "close_api_v1_db",
    "generate_uuid",
    "get_timestamp",
    "user_exists",
    "username_exists",
    "referral_code_exists",
    "serialize_doc",
    "serialize_docs",
    "create_user_doc",
    "create_order_doc",
    "create_transaction_doc"
]
