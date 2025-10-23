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
@report_bp.route('/<int:id>', methods=['POST'])
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

        data = request.get_json()
        tests = data.get("test", [])
        history_limit = data.get("history_limit")  # Optional parameter
        test_ids = [t["id"] for t in tests]
        placeholders = ', '.join(['%s'] * len(test_ids))
        query = f"""
        SELECT 
            pt.id AS patient_test_id, 
            tp.id AS test_id, 
            tp.test_name,
            tp.fee,
            tp.serology_elisa,
            tp.delivery_time
        FROM patient_tests pt
        JOIN test_profiles tp ON pt.test_id = tp.id 
        WHERE pt.patient_id = %s 
        AND pt.counter_id = %s 
        AND pt.test_id IN ({placeholders})
        """

        params = [patient_id, id] + test_ids
        cursor.execute(query, params)
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
        c.date_created AS test_datetime,
        p.parameter_name,
        p.unit,
        p.normalvalue,
        pr.result_value,
        pr.cutoff_value,
        pr.patient_test_id
    FROM parameters p
    JOIN patient_results pr 
        ON pr.parameter_id = p.id
    JOIN patient_tests pt 
        ON pr.test_profile_id = pt.test_id
        AND pt.patient_id = %s
       
    JOIN counter c 
        ON pt.counter_id = c.id
    WHERE pt.test_id = %s
      AND p.test_profile_id = pt.test_id
    ORDER BY c.date_created ASC
""", (patient_id, test_id))



            history_rows = cursor.fetchall()
            if history_limit and isinstance(history_limit, int):
                history_rows = history_rows[:history_limit]

            parameters_dict = {}
            date_set = []
            seen_dates = set()

            for row in history_rows:
                date_str = str(row['test_datetime'])
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    date_set.append(date_str)

                pname = row['parameter_name']
                if pname not in parameters_dict:
                    parameters_dict[pname] = {
                        "parameter_name": pname,
                        "unit": row['unit'],
                        "normalvalue": row['normalvalue'],
                        "results_by_date": {},
                        "cutoff_by_date": {}
                    }

                parameters_dict[pname]["results_by_date"][date_str] = row['result_value']
                parameters_dict[pname]["cutoff_by_date"][date_str] = row.get('cutoff_value')

            parameters = []
            for pname, pdata in parameters_dict.items():
                results = []
                cutoffs = []
                for d in date_set:
                    results.append(pdata["results_by_date"].get(d, "-"))
                    cutoffs.append(pdata["cutoff_by_date"].get(d))
                parameters.append({
                    "parameter_name": pdata["parameter_name"],
                    "unit": pdata["unit"],
                    "normalvalue": pdata["normalvalue"],
                    "cutoff_value": cutoffs,
                    "result_value": results
                })

            test_list.append({
                "test_name": test['test_name'],
                "fee": fee,
                "test_type": test.get('serology_elisa'),
                "delivery_time": test.get('reporting_time'),
                "dates": date_set,
                "parameters": parameters
            })

        # Generate QR Code
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

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
