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
@invoice_bp.route('/<int:patient_id>', methods=['GET'])
def generate_invoice(patient_id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Step 1: Get patient basic info
        cursor.execute("""
            SELECT id, patient_name, cell, gender, age, company, email, address, priority, remarks
            FROM patient_entry
            WHERE id = %s
        """, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({"status": 404, "message": "Patient not found"}), 404

        #  Step 2: Get all tests linked to this patient
        cursor.execute("""
            SELECT pt.id AS patient_test_id, tp.id AS test_id, tp.test_name
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pt.patient_id = %s
        """, (patient_id,))
        tests = cursor.fetchall()

        test_list = []
        for test in tests:
            test_id = test['test_id']
            patient_test_id = test['patient_test_id']

            #  Step 3: For each test, get parameters and their results
            cursor.execute("""
                SELECT 
                    p.parameter_name,
                    p.unit,
                    p.normalvalue,
                    pr.result_value
                FROM parameters p
                LEFT JOIN patient_results pr
                    ON pr.parameter_id = p.id
                    AND pr.patient_test_id = %s
                    AND pr.test_profile_id = %s
                WHERE p.test_profile_id = %s
            """, (patient_test_id, test_id, test_id))

            parameters = cursor.fetchall()
            test_list.append({
                "test_name": test['test_name'],
                "parameters": parameters
            })

        #  Step 4: Generate QR Code for invoice
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

        #  Step 5: Final JSON Response
        invoice_data = {
            "status": 200,
            "message": "Invoice generated successfully",
            "patient": {
                "patient_id": patient['id'],
                "patient_name": patient['patient_name'],
                "cell": patient['cell'],
                "gender": patient['gender'],
                "age": patient['age'],
                "company": patient['company'],
                "email": patient['email'],
                "address": patient['address'],
                "priority": patient['priority'],
                "remarks": patient['remarks'],
                "invoice_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "tests": test_list,
            "qr_code": qr_data_url
        }

        return jsonify(invoice_data), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
