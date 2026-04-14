# SQL Diff — Data Comparison Engine

Connect directly to SQL Server, run any SELECT query, and compare rows to detect changes.

---

## Quick Start

### Windows
Double-click `START_WINDOWS.bat` — it installs dependencies and opens the browser automatically.

### Mac / Linux
```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

### Manual
```bash
pip install flask flask-cors pyodbc
python server.py
# Open http://localhost:5000
```

---

## Requirements

- Python 3.7+
- SQL Server ODBC Driver (for pyodbc)
  - Windows: usually pre-installed
  - Mac: `brew install msodbcsql18`
  - Linux: see https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server

---

## Connection String Examples

```
Server=localhost;Database=MyDb;User Id=sa;Password=MyPass;
Server=myserver\SQLEXPRESS;Database=MyDb;User Id=sa;Password=MyPass;
Server=myserver,1433;Database=MyDb;User Id=sa;Password=MyPass;
Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=MyDb;Uid=sa;Pwd=MyPass;TrustServerCertificate=yes;
```

---

## Files

| File | Purpose |
|------|---------|
| `server.py` | Python backend (Flask) — handles SQL connection & comparison |
| `index.html` | Frontend — open via http://localhost:5000 |
| `START_WINDOWS.bat` | One-click start for Windows |
| `start_mac_linux.sh` | One-click start for Mac/Linux |

---

## Security

- Only SELECT queries allowed (INSERT/UPDATE/DROP etc. are blocked)
- Passwords masked in all error messages and logs
- Rate limiting applied
- Runs locally only — no data leaves your machine
