#!/usr/bin/env python3
"""
Interactive BAS Client
======================

Interactive command-line client for the Bank Application Server.
Allows manual testing of all RPC methods.

HOW TO RUN:
-----------
1. Start the BAS server in another terminal:
   python3 bas_server.py

2. Run this interactive client:
   python3 interactive_client.py

3. Follow the menu prompts

MOCK CREDENTIALS:
-----------------
neo / NeoPass123 (Balance: $10,000)
ken   / KenPass456 (Balance: $5,000)
timuthu / TimuthuPass789   (Balance: $15,000)
"""

import sys

import Pyro5.api


class InteractiveBankClient:
    """Interactive banking client."""

    def __init__(self):
        """Initialize client and connect to server."""
        self.server = None
        self.token = None
        self.username = None
        self.account_id = None
        self.connect()

    def connect(self):
        """Connect to BAS server."""
        try:
            self.server = Pyro5.api.Proxy("PYRO:bank.server@localhost:9090")
            stats = self.server.get_server_stats()
            print("✓ Connected to BAS server")
            print(f"  Active sessions: {stats['active_sessions']}")
            print(f"  Total transfers: {stats['total_transfers']}")
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            print("\nMake sure the BAS server is running:")
            print("  python3 bas_server.py")
            sys.exit(1)

    def login(self):
        """Login to the banking system."""
        print("\n" + "=" * 60)
        print("LOGIN")
        print("=" * 60)

        username = input("Username: ").strip()
        password = input("Password: ").strip()

        result = self.server.login(username, password)

        if result["success"]:
            self.token = result["token"]
            self.username = username
            self.account_id = result["account_id"]
            print("\n✓ Login successful!")
            print(f"  Account ID: {self.account_id}")
            print(f"  User ID: {result['user_id']}")
        else:
            print(f"\n✗ Login failed: {result['message']}")

    def get_balance(self):
        """Query current balance."""
        if not self.token:
            print("\n✗ Please login first")
            return

        print("\n" + "=" * 60)
        print("BALANCE QUERY")
        print("=" * 60)

        result = self.server.get_balance(self.token)

        if result["success"]:
            print(f"\n✓ Balance: ${result['balance']:,.2f}")
            print(f"  Account: {result['account_id']}")
            print(f"  Username: {result['username']}")
        else:
            print(f"\n✗ Error: {result['message']}")

    def submit_transfer(self):
        """Submit a transfer."""
        if not self.token:
            print("\n✗ Please login first")
            return

        print("\n" + "=" * 60)
        print("SUBMIT TRANSFER")
        print("=" * 60)
        print("\nAvailable accounts:")
        print("  ACC001 (neo)")
        print("  ACC002 (ken)")
        print("  ACC003 (timuthu)")

        recipient = input("\nRecipient account ID: ").strip()

        try:
            amount = float(input("Amount: $").strip())
        except ValueError:
            print("\n✗ Invalid amount")
            return

        reference = input("Reference (optional): ").strip()

        print("\nProcessing transfer...")
        result = self.server.submit_transfer(
            self.token,
            recipient,
            amount,
            reference if reference else None,
        )

        if result["success"]:
            print("\n✓ Transfer successful!")
            print(f"  Transfer ID: {result['transfer_id']}")
            print(f"  Amount: ${amount:,.2f}")
            print(f"  Fee: ${result['fee']:,.2f}")
            print(f"  Total deducted: ${result['total_deducted']:,.2f}")
            print(f"  New balance: ${result['sender_new_balance']:,.2f}")
        else:
            print(f"\n✗ Transfer failed: {result['message']}")
            if result.get("fee") is not None:
                print(f"  (Fee would have been: ${result['fee']:,.2f})")

    def get_transfer_status(self):
        """Query transfer status."""
        if not self.token:
            print("\n✗ Please login first")
            return

        print("\n" + "=" * 60)
        print("TRANSFER STATUS")
        print("=" * 60)

        transfer_id = input("Transfer ID: ").strip()

        result = self.server.get_transfer_status(self.token, transfer_id)

        if result["success"]:
            transfer = result["transfer"]
            print("\n✓ Transfer details:")
            print(f"  ID: {transfer['transfer_id']}")
            print(f"  Status: {transfer['status']}")
            print(
                "  From: "
                f"{transfer['sender_username']} "
                f"({transfer['sender_account_id']})"
            )
            print(
                "  To: "
                f"{transfer['recipient_username']} "
                f"({transfer['recipient_account_id']})"
            )
            print(f"  Amount: ${transfer['amount']:,.2f}")
            print(f"  Fee: ${transfer['fee']:,.2f}")
            print(f"  Total: ${transfer['total_deducted']:,.2f}")
            print(f"  Reference: {transfer['reference']}")
            print(f"  Timestamp: {transfer['timestamp']}")
        else:
            print(f"\n✗ Error: {result['message']}")

    def logout(self):
        """Logout from the system."""
        if not self.token:
            print("\n✗ Not logged in")
            return

        result = self.server.logout(self.token)

        if result["success"]:
            print("\n✓ Logged out successfully")
            self.token = None
            self.username = None
            self.account_id = None
        else:
            print(f"\n✗ Logout failed: {result['message']}")

    def show_menu(self):
        """Display main menu."""
        print("\n" + "=" * 60)
        print("BANK APPLICATION CLIENT")
        print("=" * 60)

        if self.token:
            print(f"Logged in as: {self.username} ({self.account_id})")
        else:
            print("Status: Not logged in")

        print("\nMenu:")
        print("  1. Login")
        print("  2. Get Balance")
        print("  3. Submit Transfer")
        print("  4. Get Transfer Status")
        print("  5. Logout")
        print("  6. Server Stats")
        print("  0. Exit")
        print("=" * 60)

    def show_stats(self):
        """Display server statistics."""
        print("\n" + "=" * 60)
        print("SERVER STATISTICS")
        print("=" * 60)

        stats = self.server.get_server_stats()
        print(f"  Total users: {stats['total_users']}")
        print(f"  Active sessions: {stats['active_sessions']}")
        print(f"  Total transfers: {stats['total_transfers']}")
        print(f"  Completed transfers: {stats['completed_transfers']}")

    def run(self):
        """Run the interactive client."""
        print("\n" + "=" * 60)
        print("INTERACTIVE BAS CLIENT")
        print("=" * 60)
        print("\nMock credentials:")
        print("  neo / NeoPass123")
        print("  ken   / KenPass456")
        print("  timuthu / TimuthuPass789")

        while True:
            self.show_menu()

            try:
                choice = input("\nChoice: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nExiting...")
                self.server._pyroRelease()
                print("✓ Connection closed")
                break

            if choice == "1":
                self.login()
            elif choice == "2":
                self.get_balance()
            elif choice == "3":
                self.submit_transfer()
            elif choice == "4":
                self.get_transfer_status()
            elif choice == "5":
                self.logout()
            elif choice == "6":
                self.show_stats()
            elif choice == "0":
                print("\nExiting...")
                self.server._pyroRelease()
                print("✓ Connection closed")
                break
            else:
                print("\n✗ Invalid choice")


def main():
    """Main entry point."""
    client = InteractiveBankClient()
    client.run()


if __name__ == "__main__":
    main()
