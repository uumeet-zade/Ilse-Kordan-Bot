import sqlite3
import json

def export():
    conn = sqlite3.connect('memory.db', timeout=15)
    conn.row_factory = sqlite3.Row
    bills = conn.execute('SELECT * FROM bills ORDER BY date DESC, id DESC').fetchall()
    
    bills_list = [dict(row) for row in bills]
    
    with open('bills.json', 'w', encoding='utf-8') as f:
        json.dump(bills_list, f, indent=4)
        
    print(f"Exported {len(bills_list)} bills to bills.json")
    
    status = conn.execute('SELECT * FROM system_status WHERE id = 1').fetchone()
    row = conn.execute('SELECT last_update FROM system_status WHERE id = 1').fetchone()
    if row:
        from datetime import datetime, timezone
        
        last_ts = float(row[0])
        
        # Format the time nicely for display
        last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        formatted_time = last_dt.strftime("%d %b %Y, %H:%M UTC")
        
        status_data = {
            "online": True, 
            "last_update": formatted_time,
            "timestamp": last_ts
        }
        with open('status.json', 'w') as f:
            json.dump(status_data, f)
        print("Exported status.json")
        
    conn.close()

if __name__ == "__main__":
    export()
