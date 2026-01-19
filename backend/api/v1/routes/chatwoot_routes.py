"""
Chatwoot Integration Routes
Receives alerts/webhooks from Chatwoot and forwards to Telegram
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ..services.telegram_bot import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatwoot", tags=["Chatwoot Integration"])


# ==================== Models ====================

class ChatwootAlert(BaseModel):
    """Chatwoot alert payload"""
    severity: str = Field(..., description="Alert severity: low, medium, high, critical")
    reason: str = Field(..., description="Handoff reason")
    conversation_id: int = Field(..., description="Chatwoot conversation ID")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    message: str = Field(..., description="Customer message")
    timestamp: Optional[str] = Field(None, description="Alert timestamp")
    chatwoot_url: Optional[str] = Field(None, description="Direct link to conversation")
    additional_info: Optional[dict] = Field(None, description="Any additional metadata")


class ChatwootWebhook(BaseModel):
    """Generic Chatwoot webhook payload"""
    event: str = Field(..., description="Event type (e.g., 'message_created', 'conversation_status_changed')")
    conversation: Optional[dict] = None
    message: Optional[dict] = None
    sender: Optional[dict] = None
    account: Optional[dict] = None


# ==================== Helper Functions ====================

def format_alert_message(alert: ChatwootAlert) -> str:
    """Format alert for Telegram with proper HTML formatting"""
    
    # Emoji based on severity
    severity_emoji = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🟠",
        "critical": "🔴"
    }
    
    emoji = severity_emoji.get(alert.severity.lower(), "⚠️")
    
    # Build message
    lines = [
        f"{emoji} <b>CHATWOOT ALERT - {alert.severity.upper()}</b>",
        "",
        f"<b>Reason:</b> {alert.reason}",
        f"<b>Conversation ID:</b> #{alert.conversation_id}",
    ]
    
    if alert.customer_name:
        lines.append(f"<b>Customer:</b> {alert.customer_name}")
    
    if alert.customer_email:
        lines.append(f"<b>Email:</b> {alert.customer_email}")
    
    lines.append("")
    lines.append(f"<b>Message:</b>")
    lines.append(f"<i>{alert.message[:500]}{'...' if len(alert.message) > 500 else ''}</i>")
    
    if alert.timestamp:
        lines.append("")
        lines.append(f"<b>Time:</b> {alert.timestamp}")
    
    if alert.chatwoot_url:
        lines.append("")
        lines.append(f"🔗 <a href='{alert.chatwoot_url}'>View in Chatwoot</a>")
    
    if alert.additional_info:
        lines.append("")
        lines.append("<b>Additional Info:</b>")
        for key, value in alert.additional_info.items():
            lines.append(f"  • {key}: {value}")
    
    return "\n".join(lines)


def format_webhook_message(webhook: ChatwootWebhook) -> str:
    """Format generic webhook for Telegram"""
    
    lines = [
        "📬 <b>CHATWOOT WEBHOOK</b>",
        "",
        f"<b>Event:</b> {webhook.event}",
    ]
    
    if webhook.conversation:
        conv = webhook.conversation
        lines.append(f"<b>Conversation:</b> #{conv.get('id', 'N/A')}")
        if conv.get('status'):
            lines.append(f"<b>Status:</b> {conv.get('status')}")
    
    if webhook.sender:
        sender = webhook.sender
        lines.append(f"<b>From:</b> {sender.get('name', 'Unknown')}")
    
    if webhook.message:
        msg = webhook.message
        content = msg.get('content', '')
        lines.append("")
        lines.append(f"<b>Message:</b>")
        lines.append(f"<i>{content[:300]}{'...' if len(content) > 300 else ''}</i>")
    
    return "\n".join(lines)


# ==================== Routes ====================

@router.post("/alerts")
async def receive_alert(
    alert: ChatwootAlert,
    request: Request
):
    """
    Receive human handoff alerts from Chatwoot and forward to Telegram
    
    This endpoint receives structured alerts from your Chatwoot bot when:
    - Customer requests human support
    - Negative sentiment detected
    - Payment/technical issues
    - Any critical situation requiring human intervention
    """
    try:
        logger.info(f"Received Chatwoot alert: {alert.reason} - Severity: {alert.severity}")
        
        # Format message for Telegram
        telegram_message = format_alert_message(alert)
        
        # Send to Telegram
        result = await send_telegram_message(
            text=telegram_message,
            parse_mode='HTML'
        )
        
        if result:
            logger.info(f"Alert forwarded to Telegram: Conversation #{alert.conversation_id}")
            return {
                "success": True,
                "message": "Alert forwarded to Telegram",
                "telegram_message_id": result.get("message_id"),
                "conversation_id": alert.conversation_id
            }
        else:
            logger.error("Failed to forward alert to Telegram")
            return {
                "success": False,
                "message": "Failed to forward alert to Telegram",
                "conversation_id": alert.conversation_id
            }
            
    except Exception as e:
        logger.error(f"Error processing Chatwoot alert: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")


@router.post("/webhook")
async def receive_webhook(
    webhook: ChatwootWebhook,
    request: Request,
    x_chatwoot_signature: Optional[str] = Header(None)
):
    """
    Receive generic webhooks from Chatwoot
    
    Supports all Chatwoot webhook events:
    - message_created
    - message_updated  
    - conversation_created
    - conversation_status_changed
    - conversation_updated
    - etc.
    
    Optional: Add signature verification using x-chatwoot-signature header
    """
    try:
        logger.info(f"Received Chatwoot webhook: {webhook.event}")
        
        # Optional: Verify signature here if needed
        # if x_chatwoot_signature:
        #     verify_chatwoot_signature(await request.body(), x_chatwoot_signature)
        
        # Format message for Telegram
        telegram_message = format_webhook_message(webhook)
        
        # Send to Telegram
        result = await send_telegram_message(
            text=telegram_message,
            parse_mode='HTML'
        )
        
        if result:
            logger.info(f"Webhook forwarded to Telegram: {webhook.event}")
            return {
                "success": True,
                "message": "Webhook forwarded to Telegram",
                "event": webhook.event
            }
        else:
            logger.warning("Failed to forward webhook to Telegram")
            return {
                "success": False,
                "message": "Failed to forward webhook to Telegram",
                "event": webhook.event
            }
            
    except Exception as e:
        logger.error(f"Error processing Chatwoot webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "chatwoot-integration",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test")
async def test_alert():
    """
    Test endpoint to verify Telegram forwarding is working
    Send a test alert to Telegram
    """
    test_alert = ChatwootAlert(
        severity="medium",
        reason="TEST_ALERT",
        conversation_id=12345,
        customer_name="Test Customer",
        customer_email="test@example.com",
        message="This is a test alert from the Chatwoot integration endpoint.",
        timestamp=datetime.utcnow().isoformat(),
        chatwoot_url="https://app.chatwoot.com/app/accounts/1/conversations/12345",
        additional_info={
            "test": True,
            "source": "API test endpoint"
        }
    )
    
    telegram_message = format_alert_message(test_alert)
    result = await send_telegram_message(text=telegram_message, parse_mode='HTML')
    
    if result:
        return {
            "success": True,
            "message": "Test alert sent to Telegram",
            "telegram_message_id": result.get("message_id")
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to send test alert to Telegram")
