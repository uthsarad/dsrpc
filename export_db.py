#!/usr/bin/env python3
"""
Database Export Utility
========================

Export SQLite database tables to CSV files for submission documentation.

HOW TO RUN:
-----------
python3 export_db.py

Creates CSV files:
- users.csv
- accounts.csv
- transfers.csv
- audit_log.csv (if exists)
"""

import csv
import os
import sqlite3


def export_table_to_csv(db_path: str, table_name: str, output_dir: str = "."):
    """
    Export a database table to CSV.

    Args:
        db_path: Path to SQLite database
        table_name: Name of table to export
        output_dir: Directory to save CSV file
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            print(f"  ⚠ Table '{table_name}' is empty")
            return

        # Get column names
        column_names = rows[0].keys()

        # Create CSV file
        csv_path = os.path.join(output_dir, f"{table_name}.csv")

        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow(column_names)

            # Write data rows
            for row in rows:
                # Convert balance_cents to dollars for readability
                row_data = []
                for i, col_name in enumerate(column_names):
                    value = row[i]

                    # Convert cents to dollars for display
                    if col_name.endswith("_cents"):
                        value = f"${value / 100:.2f}" if value is not None else ""

                    row_data.append(value)

                writer.writerow(row_data)

        print(f"  ✓ Exported {len(rows)} rows to {csv_path}")

    except sqlite3.Error as e:
        print(f"  ✗ Error exporting table '{table_name}': {e}")
    finally:
        conn.close()


def main():
    """Export all tables from the database."""
    print("=" * 70)
    print("Database Export Utility - Phase 2")
    print("=" * 70)
    print()

    db_path = "bank.db"

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"✗ Database file '{db_path}' not found")
        print("\nMake sure the BDB server has been run at least once to create the database:")
        print("  python3 bdb_server.py")
        return

    print(f"Exporting tables from: {db_path}")
    print()

    # Create exports directory
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    # Export each table
    tables = ["users", "accounts", "transfers", "audit_log"]

    for table in tables:
        print(f"Exporting table: {table}")
        export_table_to_csv(db_path, table, export_dir)

    print()
    print("=" * 70)
    print("Export Complete")
    print("=" * 70)
    print(f"\nCSV files saved to: {export_dir}/")
    print("\nFiles created:")

    for table in tables:
        csv_path = os.path.join(export_dir, f"{table}.csv")
        if os.path.exists(csv_path):
            size = os.path.getsize(csv_path)
            print(f"  - {table}.csv ({size} bytes)")

    print()


if __name__ == "__main__":
    main()
