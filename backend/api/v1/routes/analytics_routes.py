"""
API v1 Analytics Routes
Layered Analytics System:
- Layer 1: Executive Snapshot (Dashboard)
- Layer 2: Platform Trend Analytics
- Layer 3: Risk & Exposure Analytics
- Layer 4: Entity Analytics (Clients / Games)
- Layer 5: Advanced Efficiency Metrics
"""
from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import json
import logging

from ..core.database import get_db, serialize_doc, serialize_docs, get_timestamp
from ..core.timezone_helper import (
    get_client_today_range, 
    get_last_n_days_ranges, 
    get_rolling_window,
    get_last_24h_range
)
from .dependencies import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


# ==================== AUTH HELPER ====================

async def require_admin_access(request, authorization: str):
    """Require admin role for access"""
    from ..core.auth import get_current_user
    
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required", "error_code": "E1007"}
        )
    
    return user


# ==================== AUTH HELPER ====================

async def require_admin_access(request: Request, authorization: str):
    """
    Require admin role for access.
    
    SECURITY: Uses canonical auth module for consistent behavior.
    """
    from ..core.auth import get_current_user, AuthenticatedUser
    
    # Get authenticated user
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required", "error_code": "E1007"}
        )
    
    return user


# ==================== LAYER 1: EXECUTIVE SNAPSHOT (MongoDB) ====================

@router.get("/risk-snapshot", summary="Risk & Exposure Snapshot for Dashboard")
async def get_risk_snapshot(request: Request, authorization: str = Header(...)):
    """
    Risk & Exposure Snapshot (3 cards max for Dashboard) - MongoDB
    - Total Client Balance (Cash + Bonus)
    - Risk Max 24h (MAX cap-based risk from last 24h deposits)
    - Cashout Pressure Indicator
    """
    auth = await require_admin_access(request, authorization)
    
    db = await get_db()
    
    # Total client balances
    balances_pipeline = [
        {"$match": {"role": "user", "is_active": True}},
        {"$group": {
            "_id": None,
            "total_cash": {"$sum": {"$ifNull": ["$cash_balance", {"$ifNull": ["$real_balance", 0]}]}},
            "total_bonus": {"$sum": {"$ifNull": ["$bonus_balance", 0]}},
            "total_play_credits": {"$sum": {"$ifNull": ["$play_credits", 0]}},
            "total_combined": {"$sum": {
                "$add": [
                    {"$ifNull": ["$cash_balance", {"$ifNull": ["$real_balance", 0]}]},
                    {"$ifNull": ["$bonus_balance", 0]},
                    {"$ifNull": ["$play_credits", 0]}
                ]
            }}
        }}
    ]
    balances_result = await db.users.aggregate(balances_pipeline).to_list(1)
    balances = balances_result[0] if balances_result else {
        "total_cash": 0, "total_bonus": 0, "total_play_credits": 0, "total_combined": 0
    }
    
    # Get system settings for multipliers
    settings = await db.system_settings.find_one({"id": "global"})
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # RISK MAX 24H (E) - MAX(deposit_amount * withdraw_cap_multiplier) from last 24h deposits
    last_24h_start, last_24h_end = get_last_24h_range()
    approved_statuses = ['approved', 'APPROVED_EXECUTED', 'completed', 'paid']
    
    # Get last 24h deposits with their game info for per-game multiplier
    deposits_24h_pipeline = [
        {"$match": {
            "order_type": {"$in": ["game_load", "deposit"]},
            "status": {"$in": approved_statuses},
            "approved_at": {"$gte": last_24h_start, "$lte": last_24h_end}
        }},
        {"$project": {
            "amount": 1,
            "game_name": 1,
            "max_potential": {"$multiply": ["$amount", max_multiplier]}
        }},
        {"$group": {
            "_id": None,
            "risk_max": {"$max": "$max_potential"},
            "total_deposits": {"$sum": "$amount"}
        }}
    ]
    risk_result = await db.orders.aggregate(deposits_24h_pipeline).to_list(1)
    risk_max_24h = risk_result[0]["risk_max"] if risk_result else 0
    
    # Calculate pending withdrawals for pressure
    pending_statuses = ['pending_review', 'awaiting_payment_proof', 'pending', 'initiated', 'PENDING_REVIEW']
    pending_withdrawals_pipeline = [
        {"$match": {
            "order_type": {"$in": ["withdrawal", "withdrawal_game", "wallet_redeem"]},
            "status": {"$in": pending_statuses}
        }},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_amount": {"$sum": {"$ifNull": ["$amount", 0]}}
        }}
    ]
    pending_result = await db.orders.aggregate(pending_withdrawals_pipeline).to_list(1)
    pending_count = pending_result[0]["count"] if pending_result else 0
    pending_amount = pending_result[0]["total_amount"] if pending_result else 0
    
    # Cashout pressure indicator
    total_balance = float(balances.get('total_combined', 0))
    pending_ratio = (float(pending_amount) / total_balance * 100) if total_balance > 0 else 0
    
    if pending_ratio < 20:
        pressure = "low"
    elif pending_ratio < 50:
        pressure = "medium"
    else:
        pressure = "high"
    
    return {
        "total_client_balance": {
            "cash": round(float(balances.get('total_cash', 0)), 2),
            "bonus": round(float(balances.get('total_bonus', 0)), 2),
            "play_credits": round(float(balances.get('total_play_credits', 0)), 2),
            "combined": round(total_balance, 2)
        },
        "risk_max_24h": {
            "amount": round(float(risk_max_24h or 0), 2),
            "max_multiplier_used": max_multiplier,
            "description": "MAX(deposit_amount * multiplier) from last 24h deposits"
        },
        "probable_max_cashout": {
            "amount": round(min(total_balance, float(risk_max_24h or 0)), 2),
            "max_multiplier_used": max_multiplier
        },
        "cashout_pressure": {
            "indicator": pressure,
            "pending_count": pending_count,
            "pending_amount": round(float(pending_amount), 2),
            "pressure_ratio_percent": round(pending_ratio, 1)
        }
    }


# ==================== LAYER 2: PLATFORM TRENDS (MongoDB) ====================

@router.get("/platform-trends", summary="30-day trend data for charts")
async def get_platform_trends(request: Request, days: int = 30, authorization: str = Header(...)):
    """
    Platform Trends - Last N days (default 30) - MongoDB
    
    Returns daily buckets based on approved_at (client timezone day boundaries):
    - deposits = sum(game_load.amount)
    - withdrawals_paid = sum(withdrawal_game.payout_amount)
    - bonus_issued = sum(max(total_credited - amount, 0)) on game_load
    - bonus_voided = sum(void_amount) from redemptions
    - net_profit = deposits - withdrawals_paid - referral_earnings_paid
    - referral_earnings_paid = sum of paid referral earnings
    - active_clients = count distinct users with approved deposit
    """
    auth = await require_admin_access(request, authorization)
    
    db = await get_db()
    
    # Get day ranges in client timezone
    day_ranges = get_last_n_days_ranges(request, days)
    approved_statuses = ['approved', 'APPROVED_EXECUTED', 'completed', 'paid']
    
    daily_data = []
    
    # Totals for the period
    totals = {
        "deposits": 0,
        "withdrawals_paid": 0,
        "bonus_issued": 0,
        "bonus_voided": 0,
        "net_profit": 0,
        "referral_earnings_paid": 0
    }
    
    for day_start, day_end, date_label in day_ranges:
        # Deposits (game_load amount)
        deposits_pipeline = [
            {"$match": {
                "order_type": {"$in": ["game_load", "deposit", "wallet_load"]},
                "status": {"$in": approved_statuses},
                "approved_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        deposits_result = await db.orders.aggregate(deposits_pipeline).to_list(1)
        deposits = float(deposits_result[0]["total"]) if deposits_result else 0
        
        # Withdrawals paid (payout_amount)
        withdrawals_pipeline = [
            {"$match": {
                "order_type": {"$in": ["withdrawal_game", "withdrawal", "wallet_redeem"]},
                "status": {"$in": approved_statuses},
                "approved_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$payout_amount", "$amount"]}}}}
        ]
        withdrawals_result = await db.orders.aggregate(withdrawals_pipeline).to_list(1)
        withdrawals_paid = float(withdrawals_result[0]["total"]) if withdrawals_result else 0
        
        # Bonus issued = sum(total_credited - amount) where > 0
        bonus_issued_pipeline = [
            {"$match": {
                "order_type": {"$in": ["game_load", "deposit"]},
                "status": {"$in": approved_statuses},
                "approved_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$project": {
                "bonus": {"$max": [0, {"$subtract": [
                    {"$ifNull": ["$total_amount", "$amount"]}, 
                    {"$ifNull": ["$amount", 0]}
                ]}]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$bonus"}}}
        ]
        bonus_issued_result = await db.orders.aggregate(bonus_issued_pipeline).to_list(1)
        bonus_issued = float(bonus_issued_result[0]["total"]) if bonus_issued_result else 0
        
        # Bonus voided (void_amount from redemptions)
        bonus_voided_pipeline = [
            {"$match": {
                "status": {"$in": approved_statuses},
                "approved_at": {"$gte": day_start, "$lte": day_end},
                "void_amount": {"$gt": 0}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$void_amount"}}}
        ]
        bonus_voided_result = await db.orders.aggregate(bonus_voided_pipeline).to_list(1)
        bonus_voided = float(bonus_voided_result[0]["total"]) if bonus_voided_result else 0
        
        # Referral earnings paid
        referral_pipeline = [
            {"$match": {
                "status": {"$in": ["paid", "credited", "completed"]},
                "created_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        referral_result = await db.referral_earnings.aggregate(referral_pipeline).to_list(1)
        referral_earnings = float(referral_result[0]["total"]) if referral_result else 0
        
        # Net profit = deposits - withdrawals - referral_earnings
        net_profit = deposits - withdrawals_paid - referral_earnings
        
        # Active clients (distinct users with approved deposit this day)
        active_clients_pipeline = [
            {"$match": {
                "order_type": {"$in": ["game_load", "deposit"]},
                "status": {"$in": approved_statuses},
                "approved_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$group": {"_id": "$user_id"}},
            {"$count": "count"}
        ]
        active_result = await db.orders.aggregate(active_clients_pipeline).to_list(1)
        active_clients = active_result[0]["count"] if active_result else 0
        
        # Add to daily data
        daily_data.append({
            "date": date_label,
            "deposits": round(deposits, 2),
            "withdrawals_paid": round(withdrawals_paid, 2),
            "bonus_issued": round(bonus_issued, 2),
            "bonus_voided": round(bonus_voided, 2),
            "net_profit": round(net_profit, 2),
            "referral_earnings_paid": round(referral_earnings, 2),
            "active_clients": active_clients
        })
        
        # Update totals
        totals["deposits"] += deposits
        totals["withdrawals_paid"] += withdrawals_paid
        totals["bonus_issued"] += bonus_issued
        totals["bonus_voided"] += bonus_voided
        totals["net_profit"] += net_profit
        totals["referral_earnings_paid"] += referral_earnings
    
    return {
        "days": days,
        "data": daily_data,
        "totals": {
            "deposits": round(totals["deposits"], 2),
            "withdrawals_paid": round(totals["withdrawals_paid"], 2),
            "bonus_issued": round(totals["bonus_issued"], 2),
            "bonus_voided": round(totals["bonus_voided"], 2),
            "net_profit": round(totals["net_profit"], 2),
            "referral_earnings_paid": round(totals["referral_earnings_paid"], 2)
        }
    }


# ==================== LAYER 3: RISK & EXPOSURE ANALYTICS ====================

@router.get("/risk-exposure", summary="Full Risk & Exposure Report")
async def get_risk_exposure(
    request: Request,
    authorization: str = Header(...)
):
    """
    Full Risk & Exposure Analytics for Reports page
    """
    auth = await require_admin_access(request, authorization)
    
    # SECTION A: Platform Exposure
    exposure = await fetch_one("""
        SELECT 
            COALESCE(SUM(real_balance), 0) as total_cash,
            COALESCE(SUM(bonus_balance), 0) as total_bonus,
            COALESCE(SUM(play_credits), 0) as total_play_credits,
            COALESCE(SUM(real_balance + bonus_balance + COALESCE(play_credits, 0)), 0) as combined_balance,
            COALESCE(SUM(CASE WHEN withdraw_locked = TRUE THEN real_balance + bonus_balance ELSE 0 END), 0) as locked_balance,
            COALESCE(SUM(CASE WHEN withdraw_locked = FALSE THEN real_balance ELSE 0 END), 0) as withdrawable_cash
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    min_multiplier = float(settings.get('min_cashout_multiplier', 1) if settings else 1)
    
    # SECTION B: Probable Max Cashout by Game
    game_exposure = await fetch_all("""
        SELECT 
            g.game_name,
            g.display_name,
            COALESCE(SUM(o.amount) FILTER (WHERE o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'), 0) as total_deposited,
            COALESCE(SUM(o.payout_amount) FILTER (WHERE o.order_type = 'withdrawal' AND o.status = 'APPROVED_EXECUTED'), 0) as total_withdrawn
        FROM games g
        LEFT JOIN orders o ON g.game_name = o.game_name
        GROUP BY g.game_id, g.game_name, g.display_name
        ORDER BY total_deposited DESC
    """)
    
    # SECTION B: Probable Max Cashout by Client Tier
    # High-risk, Regular, VIP (based on deposit amount)
    client_tiers = await fetch_all("""
        SELECT 
            CASE 
                WHEN total_deposited >= 1000 THEN 'vip'
                WHEN total_deposited >= 100 THEN 'regular'
                ELSE 'new'
            END as tier,
            COUNT(*) as client_count,
            COALESCE(SUM(real_balance), 0) as total_cash,
            COALESCE(SUM(bonus_balance), 0) as total_bonus,
            COALESCE(SUM(total_deposited), 0) as total_deposited
        FROM users 
        WHERE role = 'user' AND is_active = TRUE
        GROUP BY CASE 
            WHEN total_deposited >= 1000 THEN 'vip'
            WHEN total_deposited >= 100 THEN 'regular'
            ELSE 'new'
        END
    """)
    
    # SECTION C: Bonus Risk
    bonus_stats = await fetch_one("""
        SELECT 
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_issued,
            COALESCE(SUM(bonus_consumed) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_converted,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_voided
        FROM orders
    """)
    
    # Current bonus at risk (still in user balances)
    bonus_at_risk = await fetch_one("""
        SELECT COALESCE(SUM(bonus_balance), 0) as total
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # SECTION D: Client Risk Table (Top 10 by balance)
    client_risk = await fetch_all("""
        SELECT 
            user_id, username, display_name,
            real_balance, bonus_balance, play_credits,
            total_deposited, total_withdrawn,
            is_suspicious, withdraw_locked
        FROM users 
        WHERE role = 'user' AND is_active = TRUE
        ORDER BY (real_balance + bonus_balance) DESC
        LIMIT 10
    """)
    
    # SECTION D: Game Risk Table
    game_risk = await fetch_all("""
        SELECT 
            g.game_name,
            g.display_name,
            COUNT(DISTINCT o.user_id) as active_players,
            COALESCE(SUM(o.amount) FILTER (WHERE o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'), 0) as total_in,
            COALESCE(SUM(o.payout_amount) FILTER (WHERE o.order_type = 'withdrawal' AND o.status = 'APPROVED_EXECUTED'), 0) as total_out,
            COALESCE(SUM(o.bonus_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as bonus_given,
            COALESCE(SUM(o.void_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as voided
        FROM games g
        LEFT JOIN orders o ON g.game_name = o.game_name
        GROUP BY g.game_id, g.game_name, g.display_name
        ORDER BY total_in DESC
    """)
    
    return {
        "platform_exposure": {
            "total_cash_balance": round(float(exposure['total_cash'] or 0), 2),
            "total_bonus_balance": round(float(exposure['total_bonus'] or 0), 2),
            "total_play_credits": round(float(exposure['total_play_credits'] or 0), 2),
            "combined_balance": round(float(exposure['combined_balance'] or 0), 2),
            "locked_balance": round(float(exposure['locked_balance'] or 0), 2),
            "withdrawable_balance": round(float(exposure['withdrawable_cash'] or 0), 2)
        },
        "probable_max_cashout": {
            "total_probable_max": round(float(exposure['withdrawable_cash'] or 0) * max_multiplier, 2),
            "cash_only_max": round(float(exposure['total_cash'] or 0), 2),
            "bonus_inclusive_max": round(float(exposure['combined_balance'] or 0), 2),
            "multiplier_settings": {
                "min": min_multiplier,
                "max": max_multiplier
            },
            "by_game": [{
                "game": g['game_name'],
                "display_name": g['display_name'],
                "total_deposited": round(float(g['total_deposited'] or 0), 2),
                "total_withdrawn": round(float(g['total_withdrawn'] or 0), 2),
                "max_exposure": round(float(g['total_deposited'] or 0) * max_multiplier - float(g['total_withdrawn'] or 0), 2)
            } for g in game_exposure],
            "by_tier": [{
                "tier": t['tier'],
                "client_count": t['client_count'],
                "total_balance": round(float(t['total_cash'] or 0) + float(t['total_bonus'] or 0), 2),
                "max_cashout": round(float(t['total_deposited'] or 0) * max_multiplier, 2)
            } for t in client_tiers]
        },
        "bonus_risk": {
            "bonus_issued": round(float(bonus_stats['bonus_issued'] or 0), 2),
            "bonus_converted": round(float(bonus_stats['bonus_converted'] or 0), 2),
            "bonus_voided": round(float(bonus_stats['bonus_voided'] or 0), 2),
            "bonus_at_risk": round(float(bonus_at_risk['total'] or 0), 2)
        },
        "tables": {
            "client_risk": [{
                "user_id": c['user_id'],
                "username": c['username'],
                "display_name": c['display_name'],
                "cash_balance": round(float(c['real_balance'] or 0), 2),
                "bonus_balance": round(float(c['bonus_balance'] or 0), 2),
                "total_balance": round(float(c['real_balance'] or 0) + float(c['bonus_balance'] or 0), 2),
                "total_deposited": round(float(c['total_deposited'] or 0), 2),
                "total_withdrawn": round(float(c['total_withdrawn'] or 0), 2),
                "max_eligible_cashout": round(float(c['total_deposited'] or 0) * max_multiplier, 2),
                "is_suspicious": c['is_suspicious'],
                "withdraw_locked": c['withdraw_locked']
            } for c in client_risk],
            "game_risk": [{
                "game": g['game_name'],
                "display_name": g['display_name'],
                "active_players": g['active_players'] or 0,
                "total_in": round(float(g['total_in'] or 0), 2),
                "total_out": round(float(g['total_out'] or 0), 2),
                "net_profit": round(float(g['total_in'] or 0) - float(g['total_out'] or 0), 2),
                "bonus_given": round(float(g['bonus_given'] or 0), 2),
                "voided": round(float(g['voided'] or 0), 2)
            } for g in game_risk]
        }
    }


# ==================== LAYER 4: ENTITY ANALYTICS ====================

@router.get("/client/{user_id}", summary="Client Analytics Detail")
async def get_client_analytics(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """
    Client-level Analytics for Client Detail page Analytics tab
    """
    auth = await require_admin_access(request, authorization)
    
    # Get user info
    user = await fetch_one("""
        SELECT user_id, username, display_name,
               real_balance, bonus_balance, play_credits,
               total_deposited, total_withdrawn,
               withdraw_locked, is_suspicious
        FROM users WHERE user_id = $1
    """, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Lifetime stats from orders
    lifetime = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED'), 0) as lifetime_deposits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED'), 0) as lifetime_withdrawals,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as lifetime_bonus,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as lifetime_void,
            COUNT(*) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') as deposit_count,
            COUNT(*) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED') as withdrawal_count
        FROM orders WHERE user_id = $1
    """, user_id)
    
    # Calculate max eligible cashout
    total_deposited = float(user['total_deposited'] or 0)
    current_balance = float(user['real_balance'] or 0) + float(user['bonus_balance'] or 0)
    max_eligible = min(current_balance, total_deposited * max_multiplier)
    
    # Expected void if withdrawn now
    # Void = bonus that would be forfeited
    expected_void = float(user['bonus_balance'] or 0)
    
    return {
        "user_id": user_id,
        "username": user['username'],
        "balances": {
            "cash": round(float(user['real_balance'] or 0), 2),
            "bonus": round(float(user['bonus_balance'] or 0), 2),
            "play_credits": round(float(user['play_credits'] or 0), 2),
            "total": round(current_balance, 2)
        },
        "withdrawal_status": {
            "locked": user['withdraw_locked'],
            "withdrawable": round(float(user['real_balance'] or 0), 2) if not user['withdraw_locked'] else 0,
            "locked_amount": round(current_balance if user['withdraw_locked'] else float(user['bonus_balance'] or 0), 2)
        },
        "cashout_projection": {
            "max_eligible_cashout": round(max_eligible, 2),
            "expected_void_if_withdrawn": round(expected_void, 2),
            "max_multiplier": max_multiplier,
            "total_deposited": round(total_deposited, 2)
        },
        "lifetime_stats": {
            "deposits": round(float(lifetime['lifetime_deposits'] or 0), 2),
            "withdrawals": round(float(lifetime['lifetime_withdrawals'] or 0), 2),
            "bonus_received": round(float(lifetime['lifetime_bonus'] or 0), 2),
            "voided": round(float(lifetime['lifetime_void'] or 0), 2),
            "deposit_count": lifetime['deposit_count'] or 0,
            "withdrawal_count": lifetime['withdrawal_count'] or 0
        },
        "risk_flags": {
            "is_suspicious": user['is_suspicious'],
            "withdraw_locked": user['withdraw_locked']
        }
    }


@router.get("/game/{game_name}", summary="Game Analytics Detail")
async def get_game_analytics(
    request: Request,
    game_name: str,
    authorization: str = Header(...)
):
    """
    Game-level Analytics for Game Detail
    """
    auth = await require_admin_access(request, authorization)
    
    # Get game info
    game = await fetch_one("SELECT * FROM games WHERE game_name = $1", game_name)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Analytics
    analytics = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED'), 0) as total_deposits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED'), 0) as total_withdrawals,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_issued,
            COALESCE(SUM(bonus_consumed) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_converted,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_voided,
            COUNT(DISTINCT user_id) FILTER (WHERE status = 'APPROVED_EXECUTED') as total_players,
            COUNT(DISTINCT user_id) FILTER (WHERE status = 'APPROVED_EXECUTED' AND created_at >= NOW() - INTERVAL '7 days') as active_7d
        FROM orders WHERE game_name = $1
    """, game_name)
    
    # Average balance per player
    avg_balance = await fetch_one("""
        SELECT 
            AVG(u.real_balance + u.bonus_balance) as avg_balance,
            COUNT(DISTINCT u.user_id) as player_count
        FROM users u
        JOIN orders o ON u.user_id = o.user_id
        WHERE o.game_name = $1 AND u.role = 'user'
    """, game_name)
    
    # Calculate net profit
    deposits = float(analytics['total_deposits'] or 0)
    withdrawals = float(analytics['total_withdrawals'] or 0)
    
    return {
        "game_name": game_name,
        "display_name": game['display_name'],
        "is_active": game['is_active'],
        "financial": {
            "total_deposits": round(deposits, 2),
            "total_withdrawals": round(withdrawals, 2),
            "net_profit": round(deposits - withdrawals, 2),
            "profit_margin_percent": round((deposits - withdrawals) / deposits * 100 if deposits > 0 else 0, 1)
        },
        "bonus": {
            "issued": round(float(analytics['bonus_issued'] or 0), 2),
            "converted": round(float(analytics['bonus_converted'] or 0), 2),
            "voided": round(float(analytics['bonus_voided'] or 0), 2)
        },
        "players": {
            "total": analytics['total_players'] or 0,
            "active_7d": analytics['active_7d'] or 0,
            "avg_balance": round(float(avg_balance['avg_balance'] or 0), 2)
        },
        "exposure": {
            "max_probable_cashout": round(deposits * max_multiplier - withdrawals, 2)
        }
    }


# ==================== LAYER 5: ADVANCED EFFICIENCY METRICS ====================

@router.get("/advanced-metrics", summary="Advanced Efficiency Metrics")
async def get_advanced_metrics(
    request: Request,
    days: int = 30,
    authorization: str = Header(...)
):
    """
    Advanced metrics for Reports → Advanced Analytics
    """
    auth = await require_admin_access(request, authorization)
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Bonus Conversion Ratio
    bonus_stats = await fetch_one("""
        SELECT 
            COALESCE(SUM(bonus_amount), 0) as issued,
            COALESCE(SUM(bonus_consumed), 0) as converted
        FROM orders WHERE status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    bonus_conversion = (float(bonus_stats['converted'] or 0) / float(bonus_stats['issued'] or 1)) * 100
    
    # Average time from deposit to withdrawal
    avg_time = await fetch_one("""
        WITH deposit_times AS (
            SELECT user_id, MIN(approved_at) as first_deposit
            FROM orders 
            WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED' AND approved_at >= $1
            GROUP BY user_id
        ),
        withdrawal_times AS (
            SELECT user_id, MIN(approved_at) as first_withdrawal
            FROM orders 
            WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED' AND approved_at >= $1
            GROUP BY user_id
        )
        SELECT AVG(EXTRACT(EPOCH FROM (w.first_withdrawal - d.first_deposit)) / 3600) as avg_hours
        FROM deposit_times d
        JOIN withdrawal_times w ON d.user_id = w.user_id
        WHERE w.first_withdrawal > d.first_deposit
    """, since)
    
    # % Clients never withdrawing
    total_depositors = await fetch_one("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM orders 
        WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    withdrawers = await fetch_one("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM orders 
        WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    never_withdrawn_pct = 100 - (float(withdrawers['count'] or 0) / float(total_depositors['count'] or 1)) * 100
    
    # % Bonus-only players (only have bonus balance, no cash)
    bonus_only = await fetch_one("""
        SELECT 
            COUNT(*) FILTER (WHERE real_balance <= 0 AND bonus_balance > 0) as bonus_only,
            COUNT(*) as total
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    bonus_only_pct = (float(bonus_only['bonus_only'] or 0) / float(bonus_only['total'] or 1)) * 100
    
    # Average multiplier reached (payout / deposit ratio)
    multiplier_data = await fetch_one("""
        WITH user_totals AS (
            SELECT 
                user_id,
                SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') as deposited,
                SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED') as withdrawn
            FROM orders
            WHERE created_at >= $1
            GROUP BY user_id
            HAVING SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') > 0
        )
        SELECT AVG(withdrawn / NULLIF(deposited, 0)) as avg_multiplier
        FROM user_totals
        WHERE withdrawn > 0
    """, since)
    
    return {
        "period_days": days,
        "metrics": {
            "bonus_conversion_ratio": {
                "value": round(bonus_conversion, 1),
                "unit": "percent",
                "description": "Percentage of bonus issued that was converted to cash"
            },
            "avg_multiplier_reached": {
                "value": round(float(multiplier_data['avg_multiplier'] or 0), 2),
                "unit": "x",
                "description": "Average withdrawal / deposit ratio for users who withdrew"
            },
            "avg_deposit_to_withdrawal_hours": {
                "value": round(float(avg_time['avg_hours'] or 0), 1),
                "unit": "hours",
                "description": "Average time between first deposit and first withdrawal"
            },
            "clients_never_withdrawing_pct": {
                "value": round(never_withdrawn_pct, 1),
                "unit": "percent",
                "description": "Percentage of depositing clients who never withdrew"
            },
            "bonus_only_players_pct": {
                "value": round(bonus_only_pct, 1),
                "unit": "percent",
                "description": "Percentage of active clients with only bonus balance"
            }
        }
    }
