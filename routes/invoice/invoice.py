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

        # Step 1: Get patient info (including discount, paid, unpaid)
        cursor.execute("""
            SELECT 
                id, patient_name, cell, gender, age, company, email, address, priority, remarks,
                discount, paid, unpaid
            FROM patient_entry
            WHERE id = %s
        """, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({"status": 404, "message": "Patient not found"}), 404

        # Step 2: Get patient tests
        cursor.execute("""
            SELECT 
                pt.id AS patient_test_id, 
                tp.id AS test_id, 
                tp.test_name,
                tp.fee
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pt.patient_id = %s
        """, (patient_id,))
        tests = cursor.fetchall()

        total_fee = 0
        test_list = []

        # Step 3: Loop through each test
        for test in tests:
            test_id = test['test_id']
            patient_test_id = test['patient_test_id']
            fee = int(test.get('fee') or 0)
            total_fee += fee

            # Step 4: Get parameters + results
            cursor.execute("""
                SELECT 
                    p.parameter_name,
                    p.unit,
                    p.normalvalue,
                    COALESCE(pr.result_value, 'N/A') AS result_value
                FROM parameters p
                LEFT JOIN patient_results pr
                    ON pr.parameter_id = p.id
                    AND pr.patient_test_id = %s
                    AND pr.test_profile_id = p.test_profile_id
                WHERE p.test_profile_id = %s
            """, (patient_test_id, test_id))

            parameters = cursor.fetchall()

            test_list.append({
                "test_name": test['test_name'],
                "fee": fee,
                "parameters": parameters
            })

        # Step 5: Generate QR Code
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

        # Step 6: Calculate unpaid (if needed)
        unpaid = patient.get("unpaid")
        if unpaid is None:
            unpaid = (total_fee - patient.get("discount", 0) - patient.get("paid", 0))

        # Step 7: Final JSON response
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
            "total_fee": total_fee,
            "discount": patient['discount'],
            "paid": patient['paid'],
            "unpaid": unpaid,
            "qr_code": qr_data_url
        }

        return jsonify(invoice_data), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
