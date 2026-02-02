# CSI3344 Banking RPC System (Three-Tier)

This project implements a simple banking transfer system using Pyro5 RPC and an SQLite database.

## Architecture

- Clients (BC): `test_client.py`, `interactive_client.py`
- Application Server (BAS): `bas_server.py` (Pyro5 RPC on `localhost:9090`, object id `bank.server`)
- Database Server (BDB): `bdb_server.py` (Pyro5 RPC on `localhost:9091`, object id `bank.db`)
- Database: SQLite file `bank.db` (accessed only by BDB)

Clients talk only to BAS. BAS talks to BDB. Only BDB accesses SQLite.

## Project structure

```
.
├── bdb_server.py          # Database server (SQLite + transactions, seeds mock users)
├── bas_server.py          # Application server (sessions/tokens, validation, fee calculation)
├── fees.py                # Tiered fee calculation (caps, 2dp rounding)
├── test_client.py         # Automated end-to-end test suite
├── interactive_client.py  # Manual CLI client
├── export_db.py           # Exports SQLite tables to CSV (creates exports/)
├── test_fees.py           # Unit tests for fee calculation (optional)
└── README.md
```

Files created at runtime:
- `bank.db` — SQLite database (created/initialized by BDB if missing)
- `exports/*.csv` — exported tables (created by `export_db.py`)

## Requirements

- Python 3.13+
- Pyro5
- Pytest

Install Pyro5:

```bash
python -m pip install Pyro5
```

On some Linux environments you may need:

```bash
python -m pip install Pyro5 --break-system-packages
```

## How to run

Start servers in this order: BDB first, then BAS, then clients.

### Terminal 1: Start BDB (database server)

```bash
python bdb_server.py
```

Expected:
- Initializes/validates SQLite schema
- Creates `bank.db` if it does not exist
- Seeds mock users if the database is new
- Prints the Pyro URI for `bank.db@localhost:9091`

### Terminal 2: Start BAS (application server)

```bash
python bas_server.py
```

Expected:
- Connects to BDB
- Prints the Pyro URI for `bank.server@localhost:9090`
- Lists available RPC methods

### Terminal 3: Run tests or interactive client

Automated tests:

```bash
python test_client.py
```

Interactive client:

```bash
python interactive_client.py
```

## Mock users

| Username | Password       | Initial Balance | Account ID |
|---------:|----------------|----------------:|-----------:|
| neo    | NeoPass123  | 10000.00        | ACC001     |
| ken      | KenPass456 | 5000.00         | ACC002     |
| timuthu    | TimuthuPass789   | 15000.00        | ACC003     |

## Client-facing RPC API (BAS)

Clients call BAS on `localhost:9090`:

1. `login(username, password)` → returns session token
2. `get_balance(token)` → returns current balance
3. `submit_transfer(token, recipient_account_id, amount, reference=None)` → executes transfer
4. `get_transfer_status(token, transfer_id)` → returns transfer details
5. `logout(token)` → ends session
6. `get_server_stats()` → server statistics

BDB methods are internal (BAS calls BDB). Clients should not call BDB directly.

## Database schema (SQLite)

SQLite database file: `bank.db`

Tables (summary):
- `users(user_id, username, password, account_id)`
- `accounts(account_id, user_id, balance_cents)`
- `transfers(transfer_id, sender_user_id, recipient_user_id, amount_cents, fee_cents, status, reference, created_at)`
- `audit_log(id, event, timestamp, details)` (optional)

Money is stored as integer cents in the database to avoid floating-point precision issues.

## Fee structure

Fees are calculated by `fees.py` using the required tiered policy (caps and 2 decimal rounding).

| Transfer Amount         | Percentage | Cap per Transfer |
|-------------------------|------------|------------------|
| 0.00 – 2000.00          | 0%         | —                |
| 2000.01 – 10000.00      | 0.25%      | 20.00            |
| 10000.01 – 20000.00     | 0.20%      | 25.00            |
| 20000.01 – 50000.00     | 0.125%     | 40.00            |
| 50000.01 – 100000.00    | 0.08%      | 50.00            |
| 100000.01 and above     | 0.05%      | 100.00           |

## Atomicity and persistence

- Transfers are executed atomically inside a single SQLite transaction in BDB.
- Balances and transfer history are persistent in `bank.db`.
- Session tokens are stored in memory in BAS. Restarting BAS invalidates existing tokens.

## Resetting the database (fresh run)

Because transfers and balances persist in `bank.db`, rerunning tests without resetting the DB will change balances and may cause some transfer tests to fail due to insufficient funds.

To reset to a clean state:
1. Stop both servers
2. Delete `bank.db`
3. Start BDB, then BAS, then run the client/tests again

## Export database tables to CSV

After running tests/transfers:

```bash
python export_db.py
```

This creates an `exports/` directory containing CSV files (for example: `users.csv`, `accounts.csv`, `transfers.csv`, `audit_log.csv`).

## Troubleshooting

- BAS cannot connect to BDB: start BDB first and check port `9091`.
- Port already in use: stop other Python processes using ports `9090`/`9091`.
- Tests fail due to low balances: delete `bank.db` and rerun for a fresh seed.
