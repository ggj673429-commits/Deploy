"""
Public APIs - No authentication required
For public games site and hero slider
"""
from fastapi import APIRouter
from typing import List, Dict, Any
from ..core.database import get_db, serialize_docs

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/games")
async def get_public_games():
    """
    Get games list for public site (no auth required)
    Returns download links only, no wallet/recharge actions
    """
    db = await get_db()
    
    # Query MongoDB for active games
    cursor = db.games.find(
        {"is_active": True},
        {
            "game_id": 1,
            "game_name": 1,
            "display_name": 1,
            "description": 1,
            "thumbnail": 1,
            "category": 1,
            "is_active": 1
        }
    ).sort("display_name", 1)
    
    games = await cursor.to_list(length=100)
    games = serialize_docs(games)
    
    # Add platforms (static for now)
    for game in games:
        game["platforms"] = ["android", "ios", "pc"]
        game["downloadUrl"] = f"/downloads/{game.get('game_name', 'game')}"
    
    return {
        "success": True,
        "games": games
    }


@router.get("/slider")
async def get_hero_slider():
    """
    Get hero slider content for public site
    Returns featured games and banners
    """
    db = await get_db()
    
    # Query MongoDB for active promotions
    cursor = db.promotions.find(
        {
            "is_active": True,
            "promotion_type": {"$in": ["hero_slider", "banner"]}
        },
        {
            "promotion_id": 1,
            "title": 1,
            "description": 1,
            "image_url": 1,
            "cta_text": 1,
            "cta_url": 1,
            "promotion_type": 1,
            "display_order": 1
        }
    ).sort("display_order", 1).limit(10)
    
    slides = await cursor.to_list(length=10)
    slides = serialize_docs(slides)
    
    return {
        "success": True,
        "slides": slides
    }


@router.get("/stats")
async def get_public_stats():
    """
    Get public statistics (total users, games, etc.)
    """
    db = await get_db()
    
    # Get counts from MongoDB
    total_users = await db.users.count_documents({})
    active_games = await db.games.count_documents({"is_active": True})
    total_orders = await db.orders.count_documents({})
    
    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "active_games": active_games,
            "total_orders": total_orders
        }
    }
