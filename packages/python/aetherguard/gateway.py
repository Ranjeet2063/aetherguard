# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Universal Local Invariant Gateway Proxy
Lightweight, zero-dependency HTTP server that intercepts and audits financial transaction
proposals from any AI agent (Python, JS, Go, Rust, or raw cURL) before wallet execution.
"""

import json
import argparse
import logging
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional

from .client import AetherGuardClient
from .types import InvariantPolicy
from .policy import conservative_policy
from .errors import InvariantViolationError

logger = logging.getLogger("aetherguard.gateway")


class InvariantGatewayHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler for AetherGuard Invariant Gateway.
    """
    client: AetherGuardClient = None
    default_balance: int = 500_000_000  # Default simulated balance: 50 XLM in stroops
    event_history: list[dict] = []
    stats: dict = {
        "total_evaluated": 0,
        "approved": 0,
        "blocked": 0,
        "total_spent": 0,
    }

    def _send_json(self, status_code: int, data: dict):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        """Routes GET endpoints."""
        if self.path == "/" or self.path == "/health":
            self._send_json(200, {
                "service": "AetherGuard Invariant Gateway",
                "version": "0.2.0",
                "status": "healthy",
                "architecture": "Proposer vs Signer Enclave",
            })
        elif self.path == "/policy":
            self._send_json(200, {
                "policy": self.client.get_policy().to_dict()
            })
        elif self.path == "/events":
            self._send_json(200, {
                "events": self.event_history[-50:]
            })
        elif self.path == "/stats":
            self._send_json(200, {
                "stats": self.stats
            })
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        """Routes POST endpoints."""
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")

        try:
            payload = json.loads(post_body) if post_body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        if self.path == "/evaluate":
            self._handle_evaluate(payload)
        elif self.path == "/policy":
            self._handle_update_policy(payload)
        elif self.path == "/reset":
            self.client.reset_history()
            self.event_history.clear()
            self.stats = {"total_evaluated": 0, "approved": 0, "blocked": 0, "total_spent": 0}
            self._send_json(200, {"message": "Spend history and telemetry reset successfully"})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _handle_evaluate(self, payload: dict):
        agent_id = str(payload.get("agent_id", "unnamed-agent"))
        recipient = str(payload.get("recipient", ""))
        amount_val = payload.get("amount", 0)
        target_contract = str(payload.get("target_contract", "stellar-payment"))
        function_name = str(payload.get("function_name", "transfer"))
        asset_symbol = str(payload.get("asset_symbol", "XLM"))
        current_balance = int(payload.get("current_balance", self.default_balance))

        try:
            amount = int(amount_val)
        except (ValueError, TypeError):
            self._send_json(400, {"error": "Invalid amount: must be an integer"})
            return

        self.stats["total_evaluated"] += 1

        proposal = self.client.create_proposal(
            agent_id=agent_id,
            intent_prompt=payload.get("intent_prompt", f"Gateway transfer of {amount} to {recipient}"),
            target_contract=target_contract,
            function_name=function_name,
            recipient=recipient,
            amount=amount,
            asset_symbol=asset_symbol,
        )

        try:
            proof = self.client.evaluate_and_prove(proposal, current_account_balance=current_balance)
            self.stats["approved"] += 1
            self.stats["total_spent"] += amount

            self.event_history.append({
                "timestamp": proof.verified_at,
                "agent_id": agent_id,
                "recipient": recipient,
                "amount": str(amount),
                "status": "APPROVED",
                "digest": proof.invariant_digest_hex,
            })

            self._send_json(200, {
                "status": "APPROVED",
                "proposal_id": proof.proposal_id,
                "verified_at": proof.verified_at,
                "spent_amount": proof.spent_amount,
                "projected_balance": proof.projected_balance,
                "remaining_rolling_budget": proof.remaining_rolling_budget,
                "invariant_digest_hex": proof.invariant_digest_hex,
                "proof_status": proof.status,
            })
        except InvariantViolationError as violation:
            self.stats["blocked"] += 1

            self.event_history.append({
                "timestamp": proposal.timestamp,
                "agent_id": agent_id,
                "recipient": recipient,
                "amount": str(amount),
                "status": "BLOCKED",
                "reason": violation.reason.value,
            })

            self._send_json(403, {
                "status": "BLOCKED",
                "reason": violation.reason.value,
                "error": str(violation),
                "details": violation.details,
            })

    def _handle_update_policy(self, payload: dict):
        try:
            self.client.update_policy(**payload)
            self._send_json(200, {
                "message": "Policy updated successfully",
                "current_policy": self.client.get_policy().to_dict(),
            })
        except Exception as e:
            self._send_json(400, {"error": str(e)})

    def log_message(self, format, *args):
        # Override to suppress default noisy stdout logging unless desired
        pass


def run_gateway(
    host: str = "127.0.0.1",
    port: int = 8787,
    policy: Optional[InvariantPolicy] = None,
) -> ThreadingHTTPServer:
    """
    Initializes and starts the Threading Invariant Gateway server.
    """
    active_policy = policy or conservative_policy()
    client = AetherGuardClient(active_policy)

    class BoundHandler(InvariantGatewayHandler):
        pass

    BoundHandler.client = client

    server = ThreadingHTTPServer((host, port), BoundHandler)
    return server


def main():
    parser = argparse.ArgumentParser(description="AetherGuard Universal Local Invariant Gateway Proxy")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Port to listen on (default: 8787)")
    parser.add_argument("--floor", type=int, default=100_000_000, help="Minimum balance reserve floor in stroops (default: 10 XLM)")
    parser.add_argument("--cap", type=int, default=50_000_000, help="Single spend cap in stroops (default: 5 XLM)")
    parser.add_argument("--window-cap", type=int, default=150_000_000, help="Rolling window cap in stroops (default: 15 XLM)")
    parser.add_argument("--window-secs", type=int, default=3600, help="Rolling window duration in seconds (default: 3600s)")

    args = parser.parse_args()

    policy = InvariantPolicy(
        max_single_spend=args.cap,
        max_rolling_window_spend=args.window_cap,
        rolling_window_seconds=args.window_secs,
        min_balance_floor=args.floor,
    )

    server = run_gateway(host=args.host, port=args.port, policy=policy)
    print("=" * 70)
    print(f"🛡️  AetherGuard Universal Invariant Gateway running on http://{args.host}:{args.port}")
    print(f"   • Single Spend Cap:       {args.cap / 10_000_000:.2f} XLM")
    print(f"   • Rolling Window Cap:     {args.window_cap / 10_000_000:.2f} XLM / {args.window_secs}s")
    print(f"   • Minimum Reserve Floor:  {args.floor / 10_000_000:.2f} XLM")
    print("=" * 70)
    print("Press Ctrl+C to terminate.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down AetherGuard Invariant Gateway...")
        server.shutdown()


if __name__ == "__main__":
    main()
