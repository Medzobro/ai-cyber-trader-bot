"""
Notification Manager - مدير الإشعارات
======================================
يرسل إشعارات فورية للمستخدمين عن الصفقات والأحداث
"""
from typing import Dict, Any, Optional
from datetime import datetime

from config import config
from utils.logger import get_logger
from .messages import Messages

logger = get_logger(__name__)


class NotificationManager:
    """مدير الإشعارات الفورية"""

    def __init__(self, bot_app=None):
        self.app = bot_app  # telegram.Application instance
        self.enabled: Dict[int, bool] = {}  # user_id -> enabled

    def set_app(self, app):
        """ربط تطبيق تليجرام"""
        self.app = app

    async def send_trade_opened(self, user_id: int, trade: Dict[str, Any]):
        """إرسال إشعار فتح صفقة"""
        if not self.app or not self._is_enabled(user_id):
            return

        try:
            message = Messages.trade_opened(trade)
            await self.app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"📢 Trade notification sent to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")

    async def send_trade_closed(self, user_id: int, trade: Dict[str, Any]):
        """إرسال إشعار إغلاق صفقة"""
        if not self.app or not self._is_enabled(user_id):
            return

        try:
            message = Messages.trade_closed(trade)
            await self.app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"📢 Close notification sent to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")

    async def send_analysis_result(self, user_id: int, result: Dict[str, Any]):
        """إرسال نتيجة تحليل"""
        if not self.app:
            return

        try:
            message = Messages.analysis_result(result)
            await self.app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"❌ Failed to send analysis: {e}")

    async def send_alert(self, user_id: int, alert_type: str, message: str):
        """إرسال تنبيه عام"""
        if not self.app:
            return

        try:
            prefix = {
                "error": "🚨",
                "warning": "⚠️",
                "info": "ℹ️",
                "success": "✅",
            }.get(alert_type, "📢")

            await self.app.bot.send_message(
                chat_id=user_id,
                text=f"{prefix} {message}",
            )

        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")

    async def broadcast_to_admins(self, message: str):
        """إرسال رسالة لجميع المدراء"""
        if not self.app:
            return

        for admin_id in config.telegram.admin_ids:
            try:
                await self.app.bot.send_message(
                    chat_id=admin_id,
                    text=f"📢 [Broadcast]\n{message}",
                )
            except Exception as e:
                logger.warning(f"Failed to send to admin {admin_id}: {e}")

    def enable_notifications(self, user_id: int):
        """تفعيل الإشعارات لمستخدم"""
        self.enabled[user_id] = True

    def disable_notifications(self, user_id: int):
        """تعطيل الإشعارات لمستخدم"""
        self.enabled[user_id] = False

    def _is_enabled(self, user_id: int) -> bool:
        """التحقق من تفعيل الإشعارات"""
        return self.enabled.get(user_id, True)  # مفعل افتراضياً
