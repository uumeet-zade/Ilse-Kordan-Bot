from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'memory.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/bill/<int:bill_id>')
def bill_page(bill_id):
    try:
        conn = get_db_connection()
        bill = conn.execute('SELECT * FROM bills WHERE id = ?', (bill_id,)).fetchone()
        conn.close()
        
        if bill is None:
            return "Bill not found", 404
            
        return render_template('bill.html', bill=dict(bill))
    except Exception as e:
        return str(e), 500

@app.route('/api/bills')
def get_bills():
    try:
        conn = get_db_connection()
        bills = conn.execute('SELECT * FROM bills ORDER BY date DESC').fetchall()
        conn.close()
        
        # Convert rows to dicts
        bills_list = [dict(row) for row in bills]
        return jsonify(bills_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    try:
        from datetime import datetime
        import pytz
        
        conn = get_db_connection()
        status = conn.execute('SELECT * FROM system_status WHERE id = 1').fetchone()
        conn.close()
        
        if not status:
            return jsonify({"online": False, "last_update": "Never"})
            
        import time
        now = time.time()
        # Online if heartbeat was in the last 5 minutes (300 seconds)
        is_online = (now - status['last_heartbeat']) < 300
        
        # Convert timestamp to CET string
        if status['last_update'] > 0:
            dt = datetime.fromtimestamp(status['last_update'], tz=pytz.UTC)
            cet = dt.astimezone(pytz.timezone('Europe/Berlin'))
            last_update_str = cet.strftime("%d %b %Y, %H:%M CET")
        else:
            last_update_str = "Never"
            
        return jsonify({
            "online": is_online,
            "last_update": last_update_str
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
