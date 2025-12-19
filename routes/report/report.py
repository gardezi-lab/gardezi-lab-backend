from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
import qrcode
import base64
from io import BytesIO
from datetime import datetime
import MySQLdb.cursors
from routes.authentication.authentication import token_required

report_bp = Blueprint('report', __name__, url_prefix='/api/report')
mysql = MySQL()

# ------------------ Report API -------------------
@report_bp.route('/<int:id>', methods=['POST'])
@token_required
def generate_report(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT pt_id, reff_by, remarks, sample, total_fee, paid, discount FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()
        

        if not result:
            return jsonify({"status": 404, "message": "Counter not found"}), 404
        
        
        
        patient_id = result['pt_id']
        reff_by = result['reff_by']
        remarks = result['remarks']
        sample = result['sample']
        
        total_fee = result['total_fee']
        paid = result['paid']
        discount = result['discount']
        pt_entry_log = "Report Printerd"
        
        cursor.execute("SELECT name FROM users WHERE id = %s", (reff_by,))
        result = cursor.fetchone()
        reff_by_name=result['name']
        print("printing error", "no error by here ss33112200")
        print('pt id', patient_id)
        print('counter_id', id)
        print('log', pt_entry_log)
        
        cursor.execute("""
                INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (patient_id, id, pt_entry_log))
        #mysql.connection.commit()
        
        cursor.execute("""
            SELECT 
                id, patient_name, cell, gender, age, 
                user_id, MR_number
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
            pt.verified_by AS verified_by,
            pt.verified_at AS verified_at,
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
            verified_by_id = test['verified_by']
            verified_by_at = test['verified_at']
            patient_test_id = test['patient_test_id']
            fee = int(test.get('fee') or 0)
            total_fee += fee
            
            #first ham check kr rhe hen k es test me koi interpertation add he. agar add he to uski id
            cursor.execute("SELECT name, qualification FROM users WHERE id = %s", (verified_by_id,)) 
            resulttest = cursor.fetchone()
            verified_by_name = resulttest['name']
            print("finding line error 1021s")
            verified_by_qualification = resulttest['qualification']
            cursor.execute("SELECT interpretation FROM test_profiles WHERE id = %s", (test_id,)) 
            resulttest = cursor.fetchone()
            intprid = resulttest['interpretation']
            detaildetail = ""
            if intprid:
                cursor.execute("SELECT detail FROM interpretations WHERE id = %s", (intprid,)) 
                resulttest = cursor.fetchone()
                detaildetail = resulttest['detail']
            
            cursor.execute("SELECT comment FROM patient_tests WHERE test_id = %s AND counter_id= %s", (test_id, id,)) 
            comresult = cursor.fetchone()
            commentcomment = comresult['comment']
            # Get department againt test_id
            cursor.execute("SELECT department_id FROM test_profiles WHERE id = %s", (test_id,)) 
            testdepart = cursor.fetchone()
            departtest = testdepart['department_id']
            cursor.execute("SELECT department_name FROM departments WHERE id = %s ", (departtest,))
            result = cursor.fetchone()
            department_name = result['department_name']
            
            
            
            
            

            cursor.execute("""
    SELECT 
        c.date_created AS test_datetime,
        p.parameter_name,
        pt.counter_id AS rowcounterid,
        p.unit,
        p.sub_heading,
        p.normalvalue,
        pr.result_value,
        pr.cutoff_value,
        pr.test_profile_id
    FROM parameters p
    JOIN patient_tests pt ON p.test_profile_id = pt.test_id AND pt.patient_id = %s AND pt.counter_id <= %s
    JOIN patient_results pr ON pr.parameter_id = p.id AND pr.counter_id=pt.counter_id
    JOIN counter c ON pt.counter_id = c.id
    WHERE pt.test_id = %s 
    ORDER BY c.date_created ASC
""", (patient_id, id, test_id))
            print("testing test_id inside loop", test_id)
            
            history_rows = cursor.fetchall()
            print("history_rows", history_rows)

            parameters_dict = {}
            date_set = []
            seen_dates = set()

            for row in history_rows:
                date_str = str(row['test_datetime'])
                
                print("date string", date_str)
                print("counter id from row just checking", row['rowcounterid'])
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    date_set.append(date_str)

                pname = row['parameter_name']
                if pname not in parameters_dict:
                    parameters_dict[pname] = {
                        "parameter_name": pname,
                        "unit": row['unit'],
                        "sub_heading": row['sub_heading'],
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
                    "sub_heading": pdata["sub_heading"],
                    "normalvalue": pdata["normalvalue"],
                    "cutoff_value": cutoffs,
                    "result_value": results
                })
            test_verify_info =[{
                "name": verified_by_name,
                "qualification": verified_by_qualification,
                "verified_at": verified_by_at 
            }]    
            test_list.append({
                "test_name": test['test_name'],
                "fee": fee,
                "comment" : commentcomment,
                'intr_detail': detaildetail,
                'department':department_name,
                "test_type": test.get('serology_elisa'),
                "delivery_time": test.get('reporting_time'),
                "dates": date_set,
                "test_verify_info": test_verify_info,
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
                "reff_by": reff_by_name,
                "gender": patient['gender'],
                "age": patient['age'],
                "MR_number": patient['MR_number'],
                "sample": sample,
                "remarks": remarks,
                "invoice_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "tests": test_list,
            "total_fee": total_fee,
            "reff_by": reff_by_name,
            "discount": discount,
            "paid": paid,
            "unpaid": unpaid,
            "qr_code": qr_data_url
        }

        return jsonify(invoice_data), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500

