from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
import qrcode
import base64
from io import BytesIO
from datetime import datetime
import MySQLdb.cursors

report_bp = Blueprint('report', __name__, url_prefix='/api/report')
mysql = MySQL()

# ------------------ Report API -------------------
@report_bp.route('/<int:id>', methods=['GET'])
def generate_report(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        
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
        
        
        cursor.execute("""
            SELECT 
                pt.id AS patient_test_id, 
                tp.id AS test_id, 
                tp.test_name,
                tp.fee,
                tp.serology_elisa,
                tp.delivery_time
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id 
            WHERE pt.patient_id = %s AND  pt.counter_id = %s
        """, (patient_id, id,))
        tests = cursor.fetchall()

        total_fee = 0
        test_list = []
        
  
        for test in tests:
            test_id = test['test_id']
            patient_test_id = test['patient_test_id']
            fee = int(test.get('fee') or 0)
            total_fee += fee

            cursor.execute("""
                SELECT 
                    p.parameter_name,
                    p.unit,
                    p.normalvalue,
                    COALESCE(pr.result_value, p.default_value) AS result_value,
                    pr.cutoff_value
                FROM parameters p
                LEFT JOIN patient_results pr
                    ON pr.parameter_id = p.id
                    AND pr.patient_test_id = %s
                    AND pr.test_profile_id = p.test_profile_id
                    AND pr.counter_id = id
                WHERE p.test_profile_id = %s
            """, (patient_test_id, test_id))

            parameters = cursor.fetchall()

            test_list.append({
                "test_name": test['test_name'],
                "fee": fee,
                'test_type': test.get('serology_elisa'),
                "delivery_time": test.get('reporting_time'),
                "parameters": parameters
            })

        # Step 4: Generate QR Code
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

        #  Calculate unpaid
        unpaid = patient.get("unpaid")
        if unpaid is None:
            unpaid = (total_fee - patient.get("discount", 0) - patient.get("paid", 0))

        
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
