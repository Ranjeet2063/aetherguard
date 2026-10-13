# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Multi-Channel Webhook Alerting Engine
Dispatches real-time security alerts to Telegram, Discord, and generic webhooks
when autonomous AI agents execute transactions or when prompt-injection attacks are neutralized.
"""

import os
import time
import json
import logging
import threading
import urllib.request
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger("aetherguard.alerts")


class AlertLevel(str, Enum):
    ALL = "ALL"                      # Alert on every transaction (approved + blocked)
    VIOLATIONS_ONLY = "VIOLATIONS"  # Alert only when invariants are violated / attacks blocked
    HIGH_VALUE_ONLY = "HIGH_VALUE"  # Alert on violations + high value spends


class WebhookAlertManager:
    """
    Asynchronous, non-blocking alert dispatcher for Telegram and Discord webhooks.
    Runs dispatch operations in detached daemon threads to guarantee zero latency penalty
    on the core mathematical invariant evaluation gateway.
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
        generic_webhook_url: Optional[str] = None,
        alert_level: AlertLevel = AlertLevel.ALL,
        high_value_threshold: int = 50_000_000,  # 5 XLM in stroops
    ):
        self.telegram_token = telegram_token or os.getenv("AETHERGUARD_TELEGRAM_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("AETHERGUARD_TELEGRAM_CHAT_ID")
        self.discord_webhook_url = discord_webhook_url or os.getenv("AETHERGUARD_DISCORD_WEBHOOK")
        self.generic_webhook_url = generic_webhook_url or os.getenv("AETHERGUARD_GENERIC_WEBHOOK")
        self.alert_level = alert_level
        self.high_value_threshold = high_value_threshold

        self._last_alert_time: dict[str, float] = {}
        self._lock = threading.Lock()

    def has_active_channels(self) -> bool:
        """Returns True if at least one webhook or messaging channel is configured."""
        return bool(
            (self.telegram_token and self.telegram_chat_id)
            or self.discord_webhook_url
            or self.generic_webhook_url
        )

    def should_alert(self, status: str, amount: int) -> bool:
        """Checks if event meets the configured alert level criteria."""
        if self.alert_level == AlertLevel.ALL:
            return True
        if self.alert_level == AlertLevel.VIOLATIONS_ONLY:
            return status == "BLOCKED"
        if self.alert_level == AlertLevel.HIGH_VALUE_ONLY:
            return status == "BLOCKED" or amount >= self.high_value_threshold
        return True

    def notify_event_async(
        self,
        agent_id: str,
        amount: int,
        recipient: str,
        status: str,
        detail: str,
        timestamp: Optional[int] = None,
    ):
        """
        Dispatches alert asynchronously in a background thread.
        Never blocks the calling invariant engine.
        """
        if not self.has_active_channels():
            return

        if not self.should_alert(status, amount):
            return

        ts = timestamp or int(time.time())
        thread = threading.Thread(
            target=self._dispatch_worker,
            args=(agent_id, amount, recipient, status, detail, ts),
            daemon=True,
        )
        thread.start()

    def _dispatch_worker(
        self,
        agent_id: str,
        amount: int,
        recipient: str,
        status: str,
        detail: str,
        timestamp: int,
    ):
        """Internal worker executing HTTP dispatches."""
        amount_xlm = f"{amount / 10_000_000:.2f} XLM"

        # 1. Telegram Dispatch
        if self.telegram_token and self.telegram_chat_id:
            try:
                self._send_telegram(agent_id, amount_xlm, recipient, status, detail, timestamp)
            except Exception as e:
                logger.warning("Failed to send Telegram alert: %s", e)

        # 2. Discord Dispatch
        if self.discord_webhook_url:
            try:
                self._send_discord(agent_id, amount_xlm, recipient, status, detail, timestamp)
            except Exception as e:
                logger.warning("Failed to send Discord webhook: %s", e)

        # 3. Generic Webhook Dispatch
        if self.generic_webhook_url:
            try:
                self._send_generic(agent_id, amount, amount_xlm, recipient, status, detail, timestamp)
            except Exception as e:
                logger.warning("Failed to send generic webhook: %s", e)

    def _send_telegram(
        self, agent_id: str, amount_xlm: str, recipient: str, status: str, detail: str, ts: int
    ):
        """Sends Telegram message via Bot API."""
        time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))

        if status == "BLOCKED":
            text = (
                f"🛑 *AETHERGUARD: ATTACK BLOCKED*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Agent:* `{agent_id}`\n"
                f"• *Attempted Spend:* *{amount_xlm}*\n"
                f"• *Recipient:* `{recipient[:16]}...`\n"
                f"• *Violation:* `{detail}`\n"
                f"• *Timestamp:* {time_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ *Result: ZERO FUNDS DRAINED. ENCLAVE ISOLATED.*"
            )
        else:
            text = (
                f"✅ *AETHERGUARD: TRANSACTION APPROVED*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Agent:* `{agent_id}`\n"
                f"• *Settled Spend:* *{amount_xlm}*\n"
                f"• *Recipient:* `{recipient[:16]}...`\n"
                f"• *Proof Digest:* `{detail[:16]}...`\n"
                f"• *Timestamp:* {time_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"✨ *Invariant Satisfied. Ready for Broadcast.*"
            )

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "AetherGuard-Alerts/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass

    def _send_discord(
        self, agent_id: str, amount_xlm: str, recipient: str, status: str, detail: str, ts: int
    ):
        """Sends rich Discord embed message."""
        time_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

        if status == "BLOCKED":
            color = 0xFF2A2A  # Red
            title = "🛑 AetherGuard Security Interception"
            description = "**Adversarial prompt injection or policy breach intercepted pre-broadcast!**"
            field_name = "Violation Reason"
        else:
            color = 0x2ECC71  # Green
            title = "✅ AetherGuard Transaction Approved"
            description = "**Autonomous agent action mathematically verified.**"
            field_name = "Proof Digest"

        payload = json.dumps({
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": [
                        {"name": "Agent ID", "value": f"`{agent_id}`", "inline": True},
                        {"name": "Amount", "value": amount_xlm, "inline": True},
                        {"name": "Recipient", "value": f"`{recipient[:20]}...`", "inline": False},
                        {"name": field_name, "value": f"`{detail}`", "inline": False},
                    ],
                    "footer": {"text": "AetherGuard Sovereign Invariant Firewall • Soroban"},
                    "timestamp": time_iso,
                }
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            self.discord_webhook_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "AetherGuard-Alerts/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass

    def _send_generic(
        self, agent_id: str, amount_stroops: int, amount_xlm: str, recipient: str, status: str, detail: str, ts: int
    ):
        """Sends generic webhook POST."""
        payload = json.dumps({
            "event": "invariant_evaluation",
            "agent_id": agent_id,
            "status": status,
            "amount_stroops": amount_stroops,
            "amount_xlm": amount_xlm,
            "recipient": recipient,
            "detail": detail,
            "timestamp": ts,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.generic_webhook_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "AetherGuard-Alerts/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
