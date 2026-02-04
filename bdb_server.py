#!/usr/bin/env python3
"""
Bank Database Server (BDB) - Phase 2
=====================================

A Pyro5-based RPC server that manages the SQLite database for the banking system.
This is the ONLY component that directly accesses the database.

HOW TO RUN:
-----------
1. Install Pyro5:
   pip install Pyro5 --break-system-packages

2. Start the BDB server (must start BEFORE BAS):
   python3 bdb_server.py

3. Server will listen on localhost:9091
   Creates/initializes bank.db SQLite database on first run

DATABASE SCHEMA:
----------------
- users: user_id (PK), username (UNIQUE), password, account_id (UNIQUE)
- accounts: account_id (PK), user_id (FK), balance_cents (INTEGER)
- transfers: transfer_id (PK), sender_user_id, recipient_user_id, amount_cents,
             fee_cents, status, reference, created_at

DESIGN NOTES:
-------------
- All money stored as INTEGER cents to avoid floating-point issues
- Atomic transfers using SQLite transactions
- BAS communicates with BDB via RPC only
- Clients have NO direct access to this server
"""

import Pyro5.api
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from decimal import Decimal


@Pyro5.api.expose
class BankDatabaseServer:
    """
    Bank Database Server implementing persistent storage via SQLite.
    
    Provides RPC methods for BAS to manage users, accounts, and transfers.
    All database operations are atomic using transactions.
    """
    
    def __init__(self, db_path: str = "bank.db"):
        """Initialize the database server."""
        self.db_path = db_path
        self._init_database()
        print(f"✓ BDB Server initialized with database: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def _init_database(self):
        """Create database schema and seed initial data if needed."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    account_id TEXT UNIQUE NOT NULL
                )
            """)
            
            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    balance_cents INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create transfers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    transfer_id TEXT PRIMARY KEY,
                    sender_user_id TEXT NOT NULL,
                    recipient_user_id TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    fee_cents INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    reference TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (sender_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (recipient_user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create audit log table (optional, for tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT
                )
            """)
            
            # Check if we need to seed data
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                print("  → Seeding initial data...")
                self._seed_data(cursor)
            
            conn.commit()
            print("  → Database schema initialized")
            
        except Exception as e:
            conn.rollback()
            print(f"  ✗ Database initialization error: {e}")
            raise
        finally:
            conn.close()
    
    def _seed_data(self, cursor):
        """Seed the database with initial users (mock data)."""
        # Mock users
        users = [
            ("USER001", "neo", "NeoPass123", "ACC001", 1000000),  # $10,000.00
            ("USER002", "ken", "KenPass456", "ACC002", 500000),    # $5,000.00
            ("USER003", "timuthu", "TimuthuPass789", "ACC003", 1500000),   # $15,000.00
        ]
        
        for user_id, username, password, account_id, balance_cents in users:
            # Insert user
            cursor.execute(
                "INSERT INTO users (user_id, username, password, account_id) VALUES (?, ?, ?, ?)",
                (user_id, username, password, account_id)
            )
            
            # Insert account
            cursor.execute(
                "INSERT INTO accounts (account_id, user_id, balance_cents) VALUES (?, ?, ?)",
                (account_id, user_id, balance_cents)
            )
            
            print(f"    ✓ Created user: {username} with balance ${balance_cents / 100:.2f}")
    
    def _cents_to_decimal(self, cents: int) -> Decimal:
        """Convert cents (integer) to Decimal dollars."""
        return Decimal(cents) / Decimal(100)
    
    def _decimal_to_cents(self, amount: Decimal) -> int:
        """Convert Decimal dollars to cents (integer)."""
        return int(amount * 100)
    
    def _float_to_cents(self, amount: float) -> int:
        """Convert float dollars to cents (integer)."""
        # Round to 2 decimal places first to avoid float precision issues
        return int(round(amount * 100))
    
    @Pyro5.api.expose
    def validate_credentials(self, username: str, password: str) -> dict:
        """
        Validate user credentials.
        
        Args:
            username: User's username
            password: User's password (plain text for Phase 2 - mock)
        
        Returns:
            dict: {"success": bool, "user_id": str, "account_id": str, "message": str}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT user_id, account_id, password FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {
                    "success": False,
                    "user_id": None,
                    "account_id": None,
                    "message": "Invalid credentials"
                }
            
            if row["password"] != password:
                return {
                    "success": False,
                    "user_id": None,
                    "account_id": None,
                    "message": "Invalid credentials"
                }
            
            print(f"✓ Credentials validated for user: {username}")
            
            return {
                "success": True,
                "user_id": row["user_id"],
                "account_id": row["account_id"],
                "message": "Credentials valid"
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": None,
                "account_id": None,
                "message": f"Database error: {str(e)}"
            }
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def get_balance(self, user_id: str) -> dict:
        """
        Get account balance for a user.
        
        Args:
            user_id: User's unique ID
        
        Returns:
            dict: {"success": bool, "balance": float, "message": str}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT a.balance_cents, u.username, u.account_id 
                   FROM accounts a 
                   JOIN users u ON a.user_id = u.user_id 
                   WHERE a.user_id = ?""",
                (user_id,),
            )
            row = cursor.fetchone()
            
            if not row:
                return {
                    "success": False,
                    "balance": None,
                    "message": f"User {user_id} not found",
                    "username": None,
                    "account_id": None
                }
            
            balance = row["balance_cents"] / 100.0  # Convert cents to dollars
            
            return {
                "success": True,
                "balance": balance,
                "message": "Balance retrieved",
                "username": row["username"],
                "account_id": row["account_id"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "balance": None,
                "message": f"Database error: {str(e)}",
                "username": None,
                "account_id": None
            }
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def account_exists(self, account_id: str) -> bool:
        """
        Check if an account exists.
        
        Args:
            account_id: Account ID to check
        
        Returns:
            bool: True if account exists, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT 1 FROM accounts WHERE account_id = ?", (account_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def get_user_by_account_id(self, account_id: str) -> Optional[dict]:
        """
        Get user information by account ID.
        
        Args:
            account_id: Account ID
        
        Returns:
            dict or None: User information if found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT u.user_id, u.username, u.account_id 
                   FROM users u 
                   WHERE u.account_id = ?""",
                (account_id,),
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "account_id": row["account_id"]
            }
            
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def execute_transfer(
        self,
        sender_user_id: str,
        recipient_user_id: str,
        amount: float,
        fee: float,
        reference: Optional[str],
        transfer_id: str
    ) -> dict:
        """
        Execute a transfer atomically.
        
        This is the critical method that ensures atomicity:
        - Deducts amount + fee from sender
        - Credits amount to recipient
        - Creates transfer record
        - All in a single transaction
        
        Args:
            sender_user_id: Sender's user ID
            recipient_user_id: Recipient's user ID
            amount: Transfer amount (dollars)
            fee: Transfer fee (dollars)
            reference: Optional reference message
            transfer_id: Unique transfer ID
        
        Returns:
            dict: {"success": bool, "message": str, "sender_new_balance": float, 
                   "transfer_id": str, "timestamp": str}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Convert to cents for storage
        amount_cents = self._float_to_cents(amount)
        fee_cents = self._float_to_cents(fee)
        total_deduction_cents = amount_cents + fee_cents
        
        timestamp = datetime.now().isoformat()
        
        try:
            # Start transaction (implicit with connection)
            
            # 1. Check sender's balance
            cursor.execute(
                "SELECT balance_cents FROM accounts WHERE user_id = ?",
                (sender_user_id,)
            )
            sender_row = cursor.fetchone()
            
            if not sender_row:
                conn.rollback()
                return {
                    "success": False,
                    "message": "Sender account not found",
                    "sender_new_balance": None,
                    "transfer_id": transfer_id,
                    "timestamp": timestamp
                }
            
            sender_balance_cents = sender_row["balance_cents"]
            
            # 2. Check sufficient funds
            if sender_balance_cents < total_deduction_cents:
                # Record failed transfer
                cursor.execute(
                    """INSERT INTO transfers 
                       (transfer_id, sender_user_id, recipient_user_id, amount_cents, 
                        fee_cents, status, reference, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (transfer_id, sender_user_id, recipient_user_id, amount_cents,
                     fee_cents, "FAILED", reference or "", timestamp)
                )
                conn.commit()
                
                return {
                    "success": False,
                    "message": f"Insufficient funds: have ${sender_balance_cents / 100:.2f}, need ${total_deduction_cents / 100:.2f}",
                    "sender_new_balance": sender_balance_cents / 100.0,
                    "transfer_id": transfer_id,
                    "timestamp": timestamp
                }
            
            # 3. Deduct from sender
            new_sender_balance_cents = sender_balance_cents - total_deduction_cents
            cursor.execute(
                "UPDATE accounts SET balance_cents = ? WHERE user_id = ?",
                (new_sender_balance_cents, sender_user_id)
            )
            
            # 4. Credit recipient
            cursor.execute(
                "UPDATE accounts SET balance_cents = balance_cents + ? WHERE user_id = ?",
                (amount_cents, recipient_user_id)
            )
            
            # 5. Record successful transfer
            cursor.execute(
                """INSERT INTO transfers 
                   (transfer_id, sender_user_id, recipient_user_id, amount_cents, 
                    fee_cents, status, reference, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (transfer_id, sender_user_id, recipient_user_id, amount_cents,
                 fee_cents, "COMPLETED", reference or "", timestamp)
            )
            
            # 6. Commit transaction
            conn.commit()
            
            print(f"✓ Transfer COMPLETED: {transfer_id[:8]}... (${amount:.2f} + ${fee:.2f} fee)")
            
            return {
                "success": True,
                "message": "Transfer completed successfully",
                "sender_new_balance": new_sender_balance_cents / 100.0,
                "transfer_id": transfer_id,
                "timestamp": timestamp
            }
            
        except Exception as e:
            conn.rollback()
            
            # Try to record failed transfer
            try:
                cursor.execute(
                    """INSERT INTO transfers 
                       (transfer_id, sender_user_id, recipient_user_id, amount_cents, 
                        fee_cents, status, reference, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (transfer_id, sender_user_id, recipient_user_id, amount_cents,
                     fee_cents, "FAILED", reference or "", timestamp)
                )
                conn.commit()
            except:
                pass  # If this fails too, we tried
            
            return {
                "success": False,
                "message": f"Transfer failed: {str(e)}",
                "sender_new_balance": None,
                "transfer_id": transfer_id,
                "timestamp": timestamp
            }
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def get_transfer(self, transfer_id: str) -> dict:
        """
        Get transfer details by ID.
        
        Args:
            transfer_id: Transfer ID
        
        Returns:
            dict: Transfer details or error
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT t.*, 
                          s.username as sender_username, s.account_id as sender_account_id,
                          r.username as recipient_username, r.account_id as recipient_account_id
                   FROM transfers t
                   JOIN users s ON t.sender_user_id = s.user_id
                   JOIN users r ON t.recipient_user_id = r.user_id
                   WHERE t.transfer_id = ?""",
                (transfer_id,),
            )
            row = cursor.fetchone()
            
            if not row:
                return {
                    "success": False,
                    "transfer": None,
                    "message": f"Transfer '{transfer_id}' not found"
                }
            
            transfer = {
                "transfer_id": row["transfer_id"],
                "sender_user_id": row["sender_user_id"],
                "sender_account_id": row["sender_account_id"],
                "sender_username": row["sender_username"],
                "recipient_user_id": row["recipient_user_id"],
                "recipient_account_id": row["recipient_account_id"],
                "recipient_username": row["recipient_username"],
                "amount": row["amount_cents"] / 100.0,
                "fee": row["fee_cents"] / 100.0,
                "total_deducted": (row["amount_cents"] + row["fee_cents"]) / 100.0,
                "status": row["status"],
                "reference": row["reference"] or "",
                "timestamp": row["created_at"]
            }
            
            return {
                "success": True,
                "transfer": transfer,
                "message": "Transfer retrieved"
            }
            
        except Exception as e:
            return {
                "success": False,
                "transfer": None,
                "message": f"Database error: {str(e)}"
            }
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def list_transfers_for_user(self, user_id: str) -> dict:
        """
        List all transfers for a user (as sender or recipient).
        
        Args:
            user_id: User ID
        
        Returns:
            dict: List of transfers
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT t.*,
                          s.username as sender_username, s.account_id as sender_account_id,
                          r.username as recipient_username, r.account_id as recipient_account_id
                   FROM transfers t
                   JOIN users s ON t.sender_user_id = s.user_id
                   JOIN users r ON t.recipient_user_id = r.user_id
                   WHERE t.sender_user_id = ? OR t.recipient_user_id = ?
                   ORDER BY t.created_at DESC""",
                (user_id, user_id)
            )
            
            rows = cursor.fetchall()
            transfers = []
            
            for row in rows:
                transfers.append({
                    "transfer_id": row["transfer_id"],
                    "sender_user_id": row["sender_user_id"],
                    "sender_account_id": row["sender_account_id"],
                    "sender_username": row["sender_username"],
                    "recipient_user_id": row["recipient_user_id"],
                    "recipient_account_id": row["recipient_account_id"],
                    "recipient_username": row["recipient_username"],
                    "amount": row["amount_cents"] / 100.0,
                    "fee": row["fee_cents"] / 100.0,
                    "status": row["status"],
                    "reference": row["reference"] or "",
                    "timestamp": row["created_at"]
                })
            
            return {
                "success": True,
                "transfers": transfers,
                "count": len(transfers),
                "message": f"Found {len(transfers)} transfers"
            }
            
        except Exception as e:
            return {
                "success": False,
                "transfers": [],
                "count": 0,
                "message": f"Database error: {str(e)}"
            }
        finally:
            conn.close()
    
    @Pyro5.api.expose
    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM transfers")
            total_transfers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM transfers WHERE status = 'COMPLETED'")
            completed_transfers = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(balance_cents) FROM accounts")
            total_balance_cents = cursor.fetchone()[0] or 0
            
            return {
                "total_users": total_users,
                "total_transfers": total_transfers,
                "completed_transfers": completed_transfers,
                "total_balance": total_balance_cents / 100.0
            }
            
        finally:
            conn.close()


def main():
    """Start the BDB server."""
    print("=" * 70)
    print("Bank Database Server (BDB) - Phase 2")
    print("=" * 70)
    print()
    
    # Create server instance
    server = BankDatabaseServer()
    
    # Start Pyro5 daemon
    daemon = Pyro5.api.Daemon(host="localhost", port=9091)
    
    # Register the server object
    uri = daemon.register(server, objectId="bank.db")
    
    print()
    print("=" * 70)
    print(f"✓ BDB Server ready at: {uri}")
    print("=" * 70)
    print()
    print("Server Details:")
    print(f"  - Host: localhost")
    print(f"  - Port: 9091")
    print(f"  - Object ID: bank.db")
    print(f"  - Database: bank.db")
    print()
    print("Available RPC Methods:")
    print("  1. validate_credentials(username, password)")
    print("  2. get_balance(user_id)")
    print("  3. account_exists(account_id)")
    print("  4. get_user_by_account_id(account_id)")
    print("  5. execute_transfer(sender_user_id, recipient_user_id, amount, fee, reference, transfer_id)")
    print("  6. get_transfer(transfer_id)")
    print("  7. list_transfers_for_user(user_id)")
    print("  8. get_stats()")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    # Run the server loop
    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\n")
        print("=" * 70)
        print("Shutting down BDB Server...")
        print("=" * 70)
        stats = server.get_stats()
        print(f"Final Statistics:")
        print(f"  - Total users: {stats['total_users']}")
        print(f"  - Total transfers: {stats['total_transfers']}")
        print(f"  - Completed transfers: {stats['completed_transfers']}")
        print(f"  - Total balance: ${stats['total_balance']:,.2f}")
        print()


if __name__ == "__main__":
    main()
