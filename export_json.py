import sqlite3
import json

def export():
    conn = sqlite3.connect('memory.db')
    conn.row_factory = sqlite3.Row
    bills = conn.execute('SELECT * FROM bills ORDER BY date DESC').fetchall()
    
    bills_list = [dict(row) for row in bills]
    
    with open('bills.json', 'w', encoding='utf-8') as f:
        json.dump(bills_list, f, indent=4)
        
    print(f"Exported {len(bills_list)} bills to bills.json")
    
    status = conn.execute('SELECT * FROM system_status WHERE id = 1').fetchone()
    if status:
        import time
        from datetime import datetime
        import pytz
        
        last_update = status['last_update']
        if last_update > 0:
            dt = datetime.fromtimestamp(last_update, tz=pytz.UTC)
            cet = dt.astimezone(pytz.timezone('Europe/Berlin'))
            last_update_str = cet.strftime("%d %b %Y, %H:%M CET")
        else:
            last_update_str = "Never"
            
        status_data = {
            "online": True, # Assume online if we just ran the export
            "last_update": last_update_str
        }
        with open('status.json', 'w', encoding='utf-8') as f:
            json.dump(status_data, f)
        print("Exported status.json")
        
    conn.close()

if __name__ == "__main__":
    export()
