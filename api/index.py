import pymysql
from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# --- ข้อมูลเชื่อมต่อ TiDB ---
DB_CONFIG = {
    'host': 'gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com',
    'port': 4000,
    'user': '3u9X1eJSybJWTiy.root',
    'password': 'hpsvsU9X2pjntAr5',
    'database': 'test',
    'ssl': {'ca': '/etc/ssl/certs/ca-certificates.crt'} if os.path.exists('/etc/ssl/certs/ca-certificates.crt') else {}
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route('/verify', methods=['POST'])
def verify_license():
    data = request.json
    key = data.get('key')
    hwid = data.get('hwid')
    
    if not key or not hwid:
        return jsonify({"success": False, "message": "Missing key or HWID"})

    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM licenses WHERE license_key = %s"
            cursor.execute(sql, (key,))
            result = cursor.fetchone()

            if not result:
                return jsonify({"success": False, "message": "Invalid License Key"})

            if result['status'] == 'banned':
                return jsonify({"success": False, "message": "This key is BANNED"})

            if result['expiry_date'] < datetime.now():
                return jsonify({"success": False, "message": "License EXPIRED"})

            if result['hwid'] is None:
                update_sql = "UPDATE licenses SET hwid = %s WHERE id = %s"
                cursor.execute(update_sql, (hwid, result['id']))
                conn.commit()
                return jsonify({"success": True, "message": "Activated Successfully!", "expiry": result['expiry_date'].timestamp()})
            
            elif result['hwid'] != hwid:
                return jsonify({"success": False, "message": "HWID doesn't match!"})

            return jsonify({"success": True, "message": "Welcome back!", "expiry": result['expiry_date'].timestamp()})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database Error: {str(e)}"})
    finally:
        conn.close()

@app.route('/')
def home():
    return "API is running on Vercel!"
