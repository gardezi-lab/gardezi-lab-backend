from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
import qrcode
import base64
from io import BytesIO
from datetime import datetime
import MySQLdb.cursors

invoice_bp = Blueprint('invoice', __name__, url_prefix='/api/invoice')
mysql = MySQL()

# ------------------ Invoice API -------------------
@invoice_bp.route('/<int:id>', methods=['GET'])
def generate_invoice(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Step 1: Get patient_id using counter_id
        cursor.execute("SELECT pt_id, remarks, sample, total_fee, paid, discount FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"status": 404, "message": "Counter not found"}), 404

        patient_id = result['pt_id']
        remarks = result['remarks']
        sample = result['sample']
        total_fee = result['total_fee']
        paid = result['paid']
        discount = result['discount']
        

        # Step 2: Get patient info
        cursor.execute("""
            SELECT 
                id, patient_name, cell, gender, age, 
                users_id, MR_number
            FROM patient_entry
            WHERE id = %s
        """, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({"status": 404, "message": "Patient not found"}), 404

        # Step 3: Get patient tests
        cursor.execute("""
            SELECT 
                pt.id AS patient_test_id, 
                pt.reporting_time AS reporting_time, 
                tp.id AS test_id, 
                tp.test_name,
                tp.fee,
                tp.delivery_time
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pt.patient_id = %s
        """, (patient_id,))
        tests = cursor.fetchall()

        total_fee = 0
        test_list = []

        for test in tests:
            fee = int(test.get('fee') or 0)
            total_fee += fee

            test_list.append({
                "test_name": test['test_name'],
                "fee": fee,
                "delivery_time": test['reporting_time']
            })

        # Step 4: Generate QR Code
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

        # Step 5: Calculate unpaid
        unpaid = patient.get("unpaid")
        if unpaid is None:
            unpaid = (total_fee - patient.get("discount", 0) - patient.get("paid", 0))

        # Step 6: Final JSON response
        invoice_data = {
            "status": 200,
            "message": "Invoice generated successfully",
            "patient": {
                "patient_id": patient['id'],
                "patient_name": patient['patient_name'],
                "cell": patient['cell'],
                "user_id": patient['users_id'],
                "gender": patient['gender'],
                "age": patient['age'],
                "MR_number": patient['MR_number'],
                "sample": sample,
                "remarks": remarks,
                "invoice_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "tests": test_list,
            "total_fee": total_fee,
            "discount": discount,
            "paid": paid,
            "unpaid": unpaid,
            "qr_code": qr_data_url
        }

        return jsonify(invoice_data), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
