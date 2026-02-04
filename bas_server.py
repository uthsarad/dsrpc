#!/usr/bin/env python3
"""
Bank Application Server (BAS) - Phase 2 (Three-tier)

BC Clients <-> BAS (Pyro5) <-> BDB (Pyro5) <-> SQLite

Fixes included:
- Pyro5 proxy thread ownership: create NEW BDB Proxy per call (thread-safe).
- Pyro5 "doesn't expose any methods": explicitly expose class + RPC methods.
- get_server_stats now returns 'completed_transfers' for test_client.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Dict, Optional, Any

import Pyro5.api

from fees import compute_fee


@Pyro5.api.expose
class BankApplicationServer:
    def __init__(self, bdb_uri: str = "PYRO:bank.db@localhost:9091"):
        self.bdb_uri = bdb_uri
        self.sessions: Dict[str, str] = {}  # token -> user_id

        self._connect_to_bdb()

    # -----------------------------
    # Thread-safe BDB RPC helper
    # -----------------------------
    def _call_bdb(self, method_name: str, *args, **kwargs) -> Any:
        """
        Create a NEW Pyro5 Proxy in the current thread for each call.
        Avoids: "the calling thread is not the owner of this proxy"
        """
        proxy = Pyro5.api.Proxy(self.bdb_uri)
        proxy._pyroTimeout = 5
        try:
            return getattr(proxy, method_name)(*args, **kwargs)
        finally:
            proxy._pyroRelease()

    def _connect_to_bdb(self) -> None:
        try:
            stats = self._call_bdb("get_stats")
            print("✓ Connected to BDB server")
            print(f"  - Total users in DB: {stats.get('total_users', 0)}")
            print(f"  - Total transfers in DB: {stats.get('total_transfers', 0)}")
            print("✓ BAS Server initialized (Phase 2 - Three-tier)")
        except Exception as e:
            print(f"✗ Failed to connect to BDB server: {e}")
            print("✓ BAS Server initialized (Phase 2 - Three-tier) [BDB not reachable]")

    def _require_user(self, token: str) -> Optional[str]:
        return self.sessions.get(token)

    # -----------------------------
    # RPC methods (EXPOSED)
    # -----------------------------
    @Pyro5.api.expose
    def login(self, username: str, password: str) -> dict:
        try:
            res = self._call_bdb("validate_credentials", username, password)
            if not res.get("success"):
                return {
                    "success": False,
                    "token": None,
                    "message": res.get("message", "Invalid credentials"),
                    "user_id": None,
                    "account_id": None,
                }

            token = str(uuid.uuid4())
            self.sessions[token] = res["user_id"]
            return {
                "success": True,
                "token": token,
                "message": "Login successful",
                "user_id": res["user_id"],
                "account_id": res["account_id"],
            }
        except Exception as e:
            return {
                "success": False,
                "token": None,
                "message": f"Server error: {e}",
                "user_id": None,
                "account_id": None,
            }

    @Pyro5.api.expose
    def logout(self, token: str) -> dict:
        if token in self.sessions:
            del self.sessions[token]
            return {"success": True, "message": "Logged out"}
        return {"success": False, "message": "Invalid token"}

    @Pyro5.api.expose
    def get_balance(self, token: str) -> dict:
        user_id = self._require_user(token)
        if not user_id:
            return {"success": False, "message": "Invalid or expired token"}

        try:
            return self._call_bdb("get_balance", user_id)
        except Exception as e:
            return {"success": False, "message": f"Server error: {e}"}

    @Pyro5.api.expose
    def submit_transfer(
        self,
        token: str,
        recipient_account_id: str,
        amount: float,
        reference: Optional[str] = None,
    ) -> dict:
        user_id = self._require_user(token)
        if not user_id:
            return {"success": False, "message": "Invalid or expired token"}

        # Validate amount
        try:
            amt = float(amount)
        except Exception:
            return {"success": False, "message": "Amount must be a number"}

        if amt <= 0:
            return {"success": False, "message": "Amount must be > 0"}

        try:
            # Recipient exists?
            exists = self._call_bdb("account_exists", recipient_account_id)
            if not exists:
                return {"success": False, "message": "Recipient account not found"}

            recipient = self._call_bdb("get_user_by_account_id", recipient_account_id)
            recipient_user_id = recipient.get("user_id")
            if not recipient_user_id:
                return {"success": False, "message": "Recipient lookup failed"}

            # Prevent self-transfer
            if recipient_user_id == user_id:
                return {"success": False, "message": "Self-transfer is not allowed"}

            # Fee calculation (fees.py uses Decimal internally; we return float for client friendliness)
            fee_dec = compute_fee(amt)
            fee = float(fee_dec)

            transfer_id = str(uuid.uuid4())
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()

            # Atomic execution in BDB (transaction inside SQLite)
            res = self._call_bdb(
                "execute_transfer",
                user_id,
                recipient_user_id,
                amt,
                fee,
                reference,
                transfer_id,
            )

            # Standardize response for tests/clients
            res.setdefault("transfer_id", transfer_id)
            res.setdefault("timestamp", timestamp)

            if res.get("success"):
                res.setdefault("fee", fee)
                res.setdefault("total_deducted", round(amt + fee, 2))
                res.setdefault("created_at", timestamp)

            return res

        except Exception as e:
            return {"success": False, "message": f"Server error: {e}"}

    @Pyro5.api.expose
    def get_transfer_status(self, token: str, transfer_id: str) -> dict:
        user_id = self._require_user(token)
        if not user_id:
            return {"success": False, "message": "Invalid or expired token"}

        try:
            res = self._call_bdb("get_transfer", transfer_id)
            if not res.get("success"):
                return res

            t = res.get("transfer") or {}

            # Authorization: only sender or recipient can view
            if t.get("sender_user_id") != user_id and t.get("recipient_user_id") != user_id:
                return {"success": False, "message": "Unauthorized"}

            return res
        except Exception as e:
            return {"success": False, "message": f"Server error: {e}"}

    @Pyro5.api.expose
    def get_server_stats(self) -> dict:
        """
        Stats required by test_client.py:
          - total_users
          - active_sessions
          - total_transfers
          - completed_transfers   (this was missing and caused your KeyError)
        """
        try:
            db_stats = self._call_bdb("get_stats")
        except Exception:
            db_stats = {"total_users": 0, "total_transfers": 0, "completed_transfers": 0}

        return {
            "total_users": db_stats.get("total_users", 0),
            "active_sessions": len(self.sessions),
            "total_transfers": db_stats.get("total_transfers", 0),
            "completed_transfers": db_stats.get("completed_transfers", 0),
        }


def main() -> None:
    print("=" * 70)
    print("Bank Application Server (BAS) - Phase 2")
    print("=" * 70)
    print()

    server = BankApplicationServer()

    daemon = Pyro5.api.Daemon(host="localhost", port=9090)
    uri = daemon.register(server, objectId="bank.server")

    print()
    print("=" * 70)
    print(f"✓ BAS Server ready at: {uri}")
    print("=" * 70)
    print()
    print("Server Details:")
    print("  - Host: localhost")
    print("  - Port: 9090")
    print("  - Object ID: bank.server")
    print("  - BDB Connection: localhost:9091")
    print()
    print("Available RPC Methods:")
    print("  1. login(username, password)")
    print("  2. get_balance(token)")
    print("  3. submit_transfer(token, recipient_account_id, amount, reference)")
    print("  4. get_transfer_status(token, transfer_id)")
    print("  5. logout(token)")
    print("  6. get_server_stats()")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)

    daemon.requestLoop()


if __name__ == "__main__":
    main()
