import pymysql
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# --- ข้อมูลเชื่อมต่อ TiDB ---
DB_CONFIG = {
    'host': 'gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com',
    'port': 4000,
    'user': '3u9X1eJSybJWTiy.root',
    'password': 'hpsvsU9X2pjntAr5',
    'database': 'test',
    'ssl': {'ssl_verify_cert': False}
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
            # 1. เช็คว่ามีคีย์นี้ไหม
            sql = "SELECT * FROM licenses WHERE license_key = %s"
            cursor.execute(sql, (key,))
            result = cursor.fetchone()

            if not result:
                return jsonify({"success": False, "message": "Invalid License Key"})

            if result['status'] == 'banned':
                return jsonify({"success": False, "message": "This key is BANNED"})

            # 2. เช็คการเปิดใช้งาน (ถ้ายังไม่เคยใช้ ให้เริ่มนับเวลาตอนนี้)
            if result['activated_at'] is None:
                # คำนวณวันหมดอายุจากวันที่เริ่มใช้จริง
                duration = result['duration_days'] or 30
                activated_at = datetime.now()
                expiry_date = activated_at + timedelta(days=duration)
                
                # อัปเดตข้อมูลการเริ่มใช้ครั้งแรก
                update_sql = "UPDATE licenses SET activated_at = %s, expiry_date = %s, hwid = %s WHERE id = %s"
                cursor.execute(update_sql, (activated_at, expiry_date, hwid, result['id']))
                conn.commit()
                
                return jsonify({
                    "success": True, 
                    "message": "License Activated! Enjoy.", 
                    "expiry": expiry_date.timestamp()
                })

            # 3. ถ้าเคยเปิดใช้แล้ว ให้เช็ควันหมดอายุตามปกติ
            if result['expiry_date'] < datetime.now():
                return jsonify({"success": False, "message": "License EXPIRED"})
            
            # 4. เช็ค HWID (ต้องเป็นเครื่องเดิม)
            if result['hwid'] != hwid:
                return jsonify({"success": False, "message": "HWID doesn't match! (Locked to another PC)"})

            return jsonify({
                "success": True, 
                "message": "Welcome back!", 
                "expiry": result['expiry_date'].timestamp()
            })

    except Exception as e:
        return jsonify({"success": False, "message": f"Database Error: {str(e)}"})
    finally:
        conn.close()

@app.route('/')
def home():
    return "Private Auth API v2.0 (Wait-for-Activation) is running!"
