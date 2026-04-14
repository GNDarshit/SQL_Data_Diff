"""
SQL Diff - Python Backend v6
Run:  python server.py
Deps: pip install flask flask-cors pyodbc
"""
import csv, io, os, re
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)

try:
    import pyodbc
    PYODBC_OK = True
except ImportError:
    PYODBC_OK = False


# ── Drivers ───────────────────────────────────────────────────────────────────
def get_sql_drivers():
    if not PYODBC_OK: return []
    kw = ('sql server', 'sqlserver', 'mssql', 'odbc driver')
    return [d for d in pyodbc.drivers() if any(k in d.lower() for k in kw)]

def best_driver():
    drivers = get_sql_drivers()
    if not drivers: return None
    def ver(n):
        m = re.search(r'(\d+)', n)
        return int(m.group(1)) if m else 0
    return sorted(drivers, key=ver, reverse=True)[0]


# ── Connection string normalizer ──────────────────────────────────────────────
def normalize(raw: str) -> str:
    raw = raw.strip().rstrip(';')
    kv = {}
    for token in raw.split(';'):
        token = token.strip()
        if '=' not in token: continue
        eq = token.index('=')
        k = token[:eq].strip().lower().replace(' ', '').replace('_', '')
        v = token[eq+1:].strip().strip('{}')
        kv[k] = v

    def pick(*aliases):
        for a in aliases:
            if a in kv: return kv[a]
        return ''

    server   = pick('server','datasource','addr','address')
    database = pick('database','initialcatalog','db')
    uid      = pick('uid','userid','username','user')
    pwd      = pick('pwd','password')
    port     = pick('port')
    integrated = pick('integratedsecurity','trustedconnection') in ('true','yes','sspi')

    instance = ''
    if '\\' in server:
        server, instance = server.split('\\', 1)
    elif ',' in server and not port:
        server, port = server.split(',', 1)

    drv = best_driver() or 'ODBC Driver 18 for SQL Server'
    srv = server.strip()
    if instance: srv = f'{srv}\\{instance}'
    elif port:   srv = f'{srv},{port.strip()}'

    parts = [f'Driver={{{drv}}}', f'SERVER={srv}', f'DATABASE={database}']
    if integrated: parts.append('Trusted_Connection=yes')
    else:          parts += [f'UID={uid}', f'PWD={pwd}']
    parts += ['Encrypt=yes', 'TrustServerCertificate=yes']
    return ';'.join(parts) + ';'

def build_from_fields(p: dict) -> str:
    drv = best_driver() or 'ODBC Driver 18 for SQL Server'
    srv = p.get('server','').strip()
    if p.get('instance','').strip(): srv = f"{srv}\\{p['instance'].strip()}"
    elif p.get('port','').strip():   srv = f"{srv},{p['port'].strip()}"
    parts = [f'Driver={{{drv}}}', f'SERVER={srv}', f'DATABASE={p.get("database","").strip()}']
    if p.get('integratedSecurity'):  parts.append('Trusted_Connection=yes')
    else: parts += [f'UID={p.get("username","").strip()}', f'PWD={p.get("password","")}']
    parts += [f'Encrypt={"yes" if p.get("encrypt",True) else "no"}',
              f'TrustServerCertificate={"yes" if p.get("trustCert",True) else "no"}']
    return ';'.join(parts) + ';'

def mask(s): return re.sub(r'(PWD|Password|Pwd)=[^;]*', r'\1=***', s, flags=re.IGNORECASE)
def serialize(v):
    if v is None: return None
    if hasattr(v,'isoformat'): return v.isoformat()
    if isinstance(v,(str,int,float,bool)): return v
    return str(v)

FORBIDDEN = re.compile(r'\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|CREATE|ALTER|EXEC|EXECUTE|xp_|sp_|OPENROWSET|BULK)\b', re.IGNORECASE)
def is_safe(q): return q.strip().upper().startswith('SELECT') and not FORBIDDEN.search(q)

def diagnose(e):
    el = e.lower()
    if 'im002' in el or 'data source name not found' in el: return 'No ODBC driver installed → https://aka.ms/downloadmsodbcsql'
    if '08001' in el or 'neither dsn nor server' in el or 'invalid connection string' in el: return 'Connection string format error — use the Connection Builder to generate a valid string.'
    if 'login failed' in el: return 'Wrong username or password.'
    if 'cannot open server' in el or 'network-related' in el or 'timeout' in el: return 'Cannot reach the server — check server name/IP, port 1433, and firewall.'
    if 'ssl' in el or 'certificate' in el: return 'SSL error — enable "Trust Server Certificate".'
    if 'invalid object name' in el: return 'Table or view not found in the selected database.'
    return ''


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/api/health')
def health():
    drivers = get_sql_drivers() if PYODBC_OK else []
    return jsonify({'ok':True,'pyodbc':PYODBC_OK,'drivers':drivers,'bestDriver':best_driver()})

@app.route('/api/build-conn', methods=['POST'])
def build_conn():
    try: return jsonify({'connectionString': build_from_fields(request.json or {})})
    except Exception as e: return jsonify({'error': str(e)}), 400

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    if not PYODBC_OK: return jsonify({'success':False,'error':'pyodbc not installed. Run: pip install pyodbc'}), 400
    data = request.json or {}
    raw = data.get('connectionString','').strip()
    if not raw: return jsonify({'success':False,'error':'connectionString required'}), 400
    drivers = get_sql_drivers()
    if not drivers: return jsonify({'success':False,'drivers':[],'error':'No ODBC driver found → https://aka.ms/downloadmsodbcsql'}), 400
    try:
        cs = normalize(raw)
        conn = pyodbc.connect(cs, timeout=10)
        conn.execute('SELECT 1')
        conn.close()
        return jsonify({'success':True,'message':f'Connected! Driver: {best_driver()}','normalizedString':mask(cs),'drivers':drivers})
    except Exception as e:
        err = mask(str(e))
        cs_ = ''
        try: cs_ = mask(normalize(raw))
        except: pass
        return jsonify({'success':False,'error':err,'hint':diagnose(err),'normalizedString':cs_,'drivers':drivers}), 400

@app.route('/api/query', methods=['POST'])
def run_query():
    """Execute query and return raw rows only — no comparison logic here."""
    if not PYODBC_OK: return jsonify({'error':'pyodbc not installed'}), 400
    data = request.json or {}
    raw = data.get('connectionString','').strip()
    query = data.get('query','').strip()
    if not raw or not query: return jsonify({'error':'connectionString and query required'}), 400
    if not is_safe(query): return jsonify({'error':'Only SELECT queries are permitted.'}), 400
    if not get_sql_drivers(): return jsonify({'error':'No ODBC driver → https://aka.ms/downloadmsodbcsql'}), 400
    try:
        cs = normalize(raw)
        conn = pyodbc.connect(cs, timeout=15)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = [{columns[i]: serialize(row[i]) for i in range(len(columns))} for row in cursor.fetchall()]
        conn.close()
        return jsonify({'rows': rows, 'columns': columns})
    except Exception as e:
        err = mask(str(e))
        return jsonify({'error': err, 'hint': diagnose(err)}), 500

@app.route('/api/export', methods=['POST'])
def export_csv():
    data = request.json or {}
    rows = data.get('rows', [])
    columns = data.get('columns', [])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(columns)
    for row in rows:
        w.writerow([str(row.get(c,'') if row.get(c) is not None else '') for c in columns])
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition':'attachment; filename=sql_data.csv'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    drivers = get_sql_drivers() if PYODBC_OK else []
    print(f"\n{'='*60}")
    print(f"  SQL Diff  →  http://localhost:{port}")
    print(f"{'='*60}")
    if not PYODBC_OK:      print("  ⚠  pyodbc missing  →  pip install pyodbc")
    elif not drivers:      print("  ⚠  No ODBC driver  →  https://aka.ms/downloadmsodbcsql")
    else:                  print(f"  ✓  Driver: {best_driver()}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
