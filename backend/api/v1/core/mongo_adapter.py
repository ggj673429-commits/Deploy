"""
MongoDB Query Helpers
Provides helper functions to make MongoDB queries easier and maintain compatibility
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class MongoDBAdapter:
    """Adapter to help transition from PostgreSQL to MongoDB"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id"""
        user = await self.db.users.find_one({"user_id": user_id})
        return self._serialize(user)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        user = await self.db.users.find_one({"username": username})
        return self._serialize(user)
    
    async def get_user_by_referral_code(self, referral_code: str) -> Optional[Dict]:
        """Get user by referral code"""
        user = await self.db.users.find_one({"referral_code": referral_code})
        return self._serialize(user)
    
    async def create_user(self, user_data: Dict) -> Dict:
        """Create a new user"""
        result = await self.db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return self._serialize(user_data)
    
    async def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user fields"""
        updates["updated_at"] = datetime.utcnow()
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    async def increment_user_field(self, user_id: str, field: str, amount: float) -> bool:
        """Increment a numeric field"""
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {field: amount}, "$set": {"updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    # ==================== ORDER OPERATIONS ====================
    
    async def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """Get order by order_id"""
        order = await self.db.orders.find_one({"order_id": order_id})
        return self._serialize(order)
    
    async def get_user_orders(self, user_id: str, order_type: Optional[str] = None, 
                             status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get user orders with optional filters"""
        query = {"user_id": user_id}
        if order_type:
            query["order_type"] = order_type
        if status:
            query["status"] = status
        
        cursor = self.db.orders.find(query).sort("created_at", -1).limit(limit)
        orders = await cursor.to_list(length=limit)
        return self._serialize_list(orders)
    
    async def create_order(self, order_data: Dict) -> Dict:
        """Create a new order"""
        result = await self.db.orders.insert_one(order_data)
        order_data["_id"] = result.inserted_id
        return self._serialize(order_data)
    
    async def update_order(self, order_id: str, updates: Dict) -> bool:
        """Update order fields"""
        updates["updated_at"] = datetime.utcnow()
        result = await self.db.orders.update_one(
            {"order_id": order_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    # ==================== TRANSACTION OPERATIONS ====================
    
    async def create_transaction(self, transaction_data: Dict) -> Dict:
        """Create a new transaction"""
        result = await self.db.transactions.insert_one(transaction_data)
        transaction_data["_id"] = result.inserted_id
        return self._serialize(transaction_data)
    
    async def get_user_transactions(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get user transactions"""
        cursor = self.db.transactions.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        transactions = await cursor.to_list(length=limit)
        return self._serialize_list(transactions)
    
    # ==================== GAME ACCOUNT OPERATIONS ====================
    
    async def get_game_account(self, user_id: str) -> Optional[Dict]:
        """Get game account by user_id"""
        account = await self.db.game_accounts.find_one({"user_id": user_id})
        return self._serialize(account)
    
    async def create_game_account(self, account_data: Dict) -> Dict:
        """Create a new game account"""
        result = await self.db.game_accounts.insert_one(account_data)
        account_data["_id"] = result.inserted_id
        return self._serialize(account_data)
    
    async def update_game_account(self, user_id: str, updates: Dict) -> bool:
        """Update game account fields"""
        updates["updated_at"] = datetime.utcnow()
        result = await self.db.game_accounts.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    # ==================== REFERRAL OPERATIONS ====================
    
    async def get_referral(self, referrer_user_id: str, referee_user_id: str) -> Optional[Dict]:
        """Get referral record"""
        referral = await self.db.referrals.find_one({
            "referrer_user_id": referrer_user_id,
            "referee_user_id": referee_user_id
        })
        return self._serialize(referral)
    
    async def create_referral(self, referral_data: Dict) -> Dict:
        """Create a new referral"""
        result = await self.db.referrals.insert_one(referral_data)
        referral_data["_id"] = result.inserted_id
        return self._serialize(referral_data)
    
    async def get_referrals_by_referrer(self, referrer_user_id: str) -> List[Dict]:
        """Get all referrals for a referrer"""
        cursor = self.db.referrals.find({"referrer_user_id": referrer_user_id})
        referrals = await cursor.to_list(length=None)
        return self._serialize_list(referrals)
    
    # ==================== PROMO CODE OPERATIONS ====================
    
    async def get_promo_by_code(self, code: str) -> Optional[Dict]:
        """Get promo code by code"""
        promo = await self.db.promo_codes.find_one({"code": code.upper()})
        return self._serialize(promo)
    
    async def create_promo_code(self, promo_data: Dict) -> Dict:
        """Create a new promo code"""
        result = await self.db.promo_codes.insert_one(promo_data)
        promo_data["_id"] = result.inserted_id
        return self._serialize(promo_data)
    
    async def has_redeemed_promo(self, user_id: str, promo_id: str) -> bool:
        """Check if user has redeemed a promo code"""
        redemption = await self.db.promo_redemptions.find_one({
            "user_id": user_id,
            "promo_id": promo_id
        })
        return redemption is not None
    
    async def create_promo_redemption(self, redemption_data: Dict) -> Dict:
        """Create a new promo redemption"""
        result = await self.db.promo_redemptions.insert_one(redemption_data)
        redemption_data["_id"] = result.inserted_id
        return self._serialize(redemption_data)
    
    # ==================== ADMIN OPERATIONS ====================
    
    async def get_all_users(self, limit: int = 1000) -> List[Dict]:
        """Get all users"""
        cursor = self.db.users.find().limit(limit)
        users = await cursor.to_list(length=limit)
        return self._serialize_list(users)
    
    async def get_pending_orders(self, order_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get pending orders"""
        query = {"status": "pending"}
        if order_type:
            query["order_type"] = order_type
        
        cursor = self.db.orders.find(query).sort("created_at", -1).limit(limit)
        orders = await cursor.to_list(length=limit)
        return self._serialize_list(orders)
    
    async def get_all_promo_codes(self) -> List[Dict]:
        """Get all promo codes"""
        cursor = self.db.promo_codes.find().sort("created_at", -1)
        promos = await cursor.to_list(length=None)
        return self._serialize_list(promos)
    
    # ==================== STATISTICS ====================
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        return await self.db.users.count_documents({})
    
    async def get_active_user_count(self) -> int:
        """Get active user count"""
        return await self.db.users.count_documents({"is_active": True})
    
    async def get_order_stats(self) -> Dict[str, int]:
        """Get order statistics"""
        pipeline = [
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        cursor = self.db.orders.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        stats = {}
        for result in results:
            stats[result["_id"]] = result["count"]
        
        return stats
    
    # ==================== HELPER METHODS ====================
    
    def _serialize(self, doc: Optional[Dict]) -> Optional[Dict]:
        """Remove MongoDB _id and convert datetime to ISO string"""
        if doc is None:
            return None
        
        if "_id" in doc:
            del doc["_id"]
        
        # Convert datetime objects to ISO strings
        for key, value in doc.items():
            if isinstance(value, datetime):
                doc[key] = value.isoformat()
        
        return doc
    
    def _serialize_list(self, docs: List[Dict]) -> List[Dict]:
        """Serialize a list of documents"""
        return [self._serialize(doc) for doc in docs]


# Global adapter instance
_adapter: Optional[MongoDBAdapter] = None


async def get_adapter() -> MongoDBAdapter:
    """Get the MongoDB adapter instance"""
    global _adapter
    from .database import get_db
    
    if _adapter is None:
        db = await get_db()
        _adapter = MongoDBAdapter(db)
    
    return _adapter
