import math
from flask import Flask, request, jsonify, Blueprint, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL
from datetime import datetime
import MySQLdb
import json
import random

patient_entry_bp = Blueprint('patient_entry', __name__, url_prefix='/api/patient_entry')
mysql = MySQL()

# ================== Patient Entry CRUD Operations ================== #

# ------------------- Create Patient Entry ------------------ #
@patient_entry_bp.route('/', methods=['POST'])
# from flask import request, jsonify, current_app
def create_patient_entry():
    try:
        data = request.get_json()

        # --- Extract Fields ---
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company_id = data.get('company_id')
        users_id = data.get('reffered_by_id')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package_id = data.get('package_id')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        discount = int(data.get('discount', 0))
        total_fee = int(data.get('total_fee', 0))
        paid = int(data.get('paid', 0))
        test_list = data.get('test', [])
        print("Payload received:", data)

        # --- Validations ---
        errors = []
        if not patient_name or not str(patient_name).strip():
            errors.append("Patient name is required.")
        if age is None:
            errors.append("Age is required.")
        if not gender or not str(gender).strip():
            errors.append("Gender is required.")
        if not sample or not str(sample).strip():
            errors.append("Sample is required.")
        if not users_id:
            errors.append("users is required.")

        if errors:
            return jsonify({"errors": errors}), 400

        age = str(age)
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # --- Step 1: Insert Patient ---
        insert_query = """
        INSERT INTO patient_entry 
    (cell, patient_name, father_hasband_MR, age, gender,
     email, address, sample, priority, remarks,
     discount, paid, total_fee, users_id, company_id, package_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
        cursor.execute(insert_query, (
    cell, patient_name, father_hasband_MR, age,
    gender, email, address, sample, priority, remarks,
    discount, paid, total_fee,
    users_id,  
    company_id,      
    package_id       
))


        # --- Step 2: Get Patient ID ---
        patient_id = cursor.lastrowid

        # --- Step 3: Generate MR Number ---
        prefix = "2025-GL-"
        MR_number = f"{prefix}{patient_id}"

        cursor.execute(
            "UPDATE patient_entry SET MR_number = %s WHERE id = %s",
            (MR_number, patient_id)
        )

        # --- Step 4: Insert Tests ---
       
        inserted_tests = []

        for test_obj in test_list:
            test_id = test_obj.get("id")
            test_name = test_obj.get("name")
 

            # Insert test record for this patient
            cursor.execute("""
                INSERT INTO patient_tests 
                (patient_id, test_id, status)
                VALUES (%s, %s, %s)
            """, (patient_id, test_id,"Unverified"))

            patient_test_id = cursor.lastrowid
       

            inserted_tests.append({
                "patient_test_id": patient_test_id,
                "test_id": test_id,
                "test_name": test_name,
            })

    
        # --- Step 6: Insert into Cash Table ---
        cursor.execute(
            "INSERT INTO cash (description, dr) VALUES (%s, %s)",
            (MR_number, total_fee)
        )

        # --- Step 7: Log Activity ---
        now_time = datetime.now()
        cursor.execute(
            "INSERT INTO patient_activity_log (patient_id, activity, created_at) VALUES (%s, %s, %s)",
            (patient_id, "Patient Entry Created", now_time)
        )

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Patient entry created successfully",
            "patient_id": patient_id,
            "MR_number": MR_number,
            "tests": inserted_tests,
            "total_fee": total_fee,
            "discount": discount,
            "paid": paid
        }), 201

    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        if 'cursor' in locals():
            try:
                cursor.close()
            except Exception:
                pass
        return jsonify({"error": str(e)}), 500


#-------------------- GET selected test of patient by patient_id -----------------------
@patient_entry_bp.route('/tests/<int:patient_id>/', methods=['GET'])
def get_patient_tests(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Patient ke tests fetch karo sath test_profile_id (tp.id)
        query = """
        SELECT 
            pt.id AS patient_test_id,
            tp.id AS test_profile_id,
            tp.test_name
        FROM patient_tests pt
        JOIN test_profiles tp ON pt.test_id = tp.id
        WHERE pt.patient_id = %s
        """
        cursor.execute(query, (patient_id,))
        tests = cursor.fetchall()

        cursor.close()

        if not tests:
            return jsonify({"message": "No tests found for this patient"}), 404

        return jsonify({
            "message": "Patient tests fetched successfully",
            "patient_id": patient_id,
            "tests": tests
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#------------------ GET patient selected tests parameter by patient_test_id ---
@patient_entry_bp.route('/test_parameters/<int:test_id>/<int:patient_id>', methods=['GET'])
def get_test_parameters(test_id, patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Step 1: Fetch all parameters for this test_id
        cursor.execute("""
            SELECT id, parameter_name, unit, normalvalue, default_value
            FROM parameters
            WHERE test_profile_id = %s
        """, (test_id,))
        parameters = cursor.fetchall()

        # Step 2: Fetch existing results for this patient + test
        cursor.execute("""
            SELECT parameter_id, result_value
            FROM patient_results
            WHERE patient_id = %s AND test_profile_id = %s
        """, (patient_id, test_id))
        results = cursor.fetchall()

        # Convert results into a quick lookup dictionary
        results_dict = {r['parameter_id']: r['result_value'] for r in results}

        # Step 3: Replace default_value if result exists
        updated_parameters = []
        for param in parameters:
            parameter_id = param['id']
            if parameter_id in results_dict:
                param['default_value'] = results_dict[parameter_id]
            updated_parameters.append(param)

        cursor.close()

        return jsonify({
            "test_id": test_id,
            "patient_id": patient_id,
            "parameters": updated_parameters
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#---------------------Add result of patient selected test parameters by patient_test_id----
@patient_entry_bp.route('/test_results/<int:patient_test_id>', methods=['POST'])
def add_or_update_result(patient_test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        data = request.get_json()
        print("Request Data:", data)  # Debug print to show received data

        patient_id = data.get("patient_id")
        results = data.get("results", [])
        parameters = data.get("parameters", [])
        test_profile_id = data.get("test_profile_id")
        
        # If results list is empty, extract from parameters
        if not results and parameters:
            results = [
                {"parameter_id": p.get("parameter_id"), "result_value": p.get("result_value")}
                for p in parameters if p.get("parameter_id") and p.get("result_value")
            ]

        print("Extracted Results:", results)  # Debug print

        # --- Validation ---
        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400

        if not results or not isinstance(results, list):
            return jsonify({"error": "results list is invalid or empty"}), 400

        # --- Step 1: Get test_profile_id from patient_tests table ---
        # cursor.execute("SELECT test_profile_id FROM patient_tests WHERE id = %s", (patient_test_id,))
        # test_ref = cursor.fetchone()
        # if not test_ref:
        #     return jsonify({"error": "Invalid patient_test_id"}), 400

        # test_profile_id = test_ref['test_profile_id']

        # --- Step 2: Verify that test_profile_id exists in test_profiles ---
        cursor.execute("SELECT id, test_name FROM test_profiles WHERE id = %s", (test_profile_id,))
        test_profile = cursor.fetchone()
        if not test_profile:
            return jsonify({"error": "Test profile not found"}), 404

        # --- Step 3: Insert/Update results ---
        for result in results:
            parameter_id = result.get("parameter_id")
            result_value = result.get("result_value")

            if not parameter_id or result_value in [None, "", "NULL"]:
                continue  # skip invalid data

            # Check if record already exists
            cursor.execute("""
                SELECT id FROM patient_results
                WHERE patient_test_id = %s AND parameter_id = %s AND patient_id = %s
            """, (patient_test_id, parameter_id, patient_id))
            existing = cursor.fetchone()
            print(existing)
            if existing:
                cursor.execute("""
                    UPDATE patient_results
                    SET result_value = %s
                    WHERE id = %s
                """, (result_value, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO patient_results
                    (patient_id, patient_test_id, parameter_id, result_value, created_at, test_profile_id, is_completed)
                    VALUES (%s, %s, %s, %s, NOW(), %s, 0)
                """, (patient_id, patient_test_id, parameter_id, result_value, test_profile_id))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Results saved successfully",
            "test_profile_id": test_profile_id,
            "test_name": test_profile["test_name"],
            "results": results  #  Return the extracted results for confirmation
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- Update the test fees --------------
@patient_entry_bp.route("/update_fee/<int:id>", methods=["PUT"])
def update_fee(id):
    try:
        data = request.get_json()
        new_paid = int(data.get("paid"))

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT paid, total_fee FROM patient_entry WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"message": "Record not found"}), 404

        old_paid, total_fee = result
        total_paid = old_paid + new_paid
        total_result = total_paid - total_fee
        
        paid = total_paid
        # print("old_paid",old_paid)
        # print("total_fee",total_fee)
        # print("total_paid",total_paid)
        # print("new_paid",new_paid)
        # print("total_result",total_result)
        # print("paid",paid)
        
      
        
        cursor.execute("UPDATE patient_entry SET paid = %s WHERE id=%s", (total_paid, id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Updated", "paid": total_paid,"total": total_fee}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500        

#-------------------- GET patient test parameter result by patient_test_id -----
@patient_entry_bp.route('/get_test_results/<int:patient_id>/', methods=['GET'])
def get_test_results(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # --- Step 1: Fetch patient test results ---
        query = """
            SELECT 
                pr.id AS result_id,
                pr.patient_id,
                pr.patient_test_id,
                pr.parameter_id,
                p.parameter_name,
                p.unit,
                p.normalvalue,
                pr.result_value,
                pr.test_profile_id,
                tp.test_name,
                pr.created_at
            FROM patient_results pr
            LEFT JOIN parameters p ON pr.parameter_id = p.id
            LEFT JOIN test_profiles tp ON pr.test_profile_id = tp.id
            WHERE pr.patient_id = %s
        """
        cursor.execute(query, (patient_id,))
        results = cursor.fetchall()

        if not results:
            return jsonify({"message": "No test results found for this patient_id"}), 404

        # --- Step 2: Format the response ---
        formatted = []
        for r in results:
            formatted.append({
                "result_id": r["result_id"],
                "patient_id": r["patient_id"],
                "patient_test_id": r["patient_test_id"],
                "test_profile_id": r["test_profile_id"],
                "test_name": r["test_name"],
                "parameter_id": r["parameter_id"],
                "parameter_name": r["parameter_name"],
                "unit": r["unit"],
                "normalvalue": r["normalvalue"],
                "result_value": r["result_value"],
                "created_at": r["created_at"]
            })

        cursor.close()
        return jsonify({
            "message": "Test results fetched successfully",
            "patient_id": patient_id,
            "results": formatted
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- Get All Patient Entries (Search + Pagination) ------------------ #
@patient_entry_bp.route('/', methods=['GET'])
def get_all_patient_entries():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # search = request.args.get("search", "", type=str)
        # current_page = request.args.get("currentpage", 1, type=int)
        # record_per_page = request.args.get("recordperpage", 10, type=int)

        # offset = (current_page - 1) * record_per_page

        base_query = "SELECT * FROM patient_entry"
        where_clauses = [] 
        values = []

        # if search:
        #     where_clauses.append(
        #         "(patient_name LIKE %s OR father_hasband_MR LIKE %s OR company_id LIKE %s OR users_id LIKE %s OR gender LIKE %s OR email LIKE %s OR address LIKE %s OR package_id LIKE %s OR sample LIKE %s OR priority LIKE %s OR remarks LIKE %s OR test LIKE %s)"
        #     )
        #     for _ in range(13):
        #         values.append(f"%{search}%")

        # if where_clauses:
        #     base_query += " WHERE " + " AND ".join(where_clauses)

        # count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        # cursor.execute(count_query, values)
        # total_records = cursor.fetchone()["total"]

        # base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        # values.extend([record_per_page, offset])
        cursor.execute(base_query, values)
        patients = cursor.fetchall()

        # 🔹 Fetch each patient's tests
        test_cursor = mysql.connection.cursor(DictCursor)
        for patient in patients:
            test_cursor.execute("""
                SELECT pt.id AS patient_test_id, tp.test_name,tp.delivery_time,tp.sample_required, tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id = tp.id
                WHERE pt.patient_id = %s
            """, (patient["id"],))
            tests = test_cursor.fetchall()
            patient["tests"] = tests  

        # total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": patients,
            # "totalRecords": total_records,
            # "totalPages": total_pages,
            # "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ------------------- Get Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['GET'])
def patient_get_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # Get patient record
        cursor.execute("SELECT * FROM patient_entry WHERE id = %s", (id,))
        patient = cursor.fetchone()

        if not patient:
            cursor.close()
            return jsonify({"error": "Patient entry not found"}), 404

        # Get patient tests
        cursor.execute("SELECT test_id FROM patient_tests WHERE patient_id = %s", (id,))
        test_rows = cursor.fetchall()
        test_ids = [t["test_id"] for t in test_rows]

        cursor.close()

        # Directly take IDs from patient_entry record
        response = {
            "patient_entry": patient,
            "tests": test_ids,
            "users_id": patient.get("users_id"),
            "company_id": patient.get("company_id"),
            "package_id": patient.get("package_id")
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Update Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['PUT'])
def update_patient_entry(id):
    try:
        data = request.get_json()

        #  patient_entry table ke fields
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        discount = data.get('discount')
        paid = data.get('paid')
        total_fee = data.get('total_fee')
        company_id = data.get('company_id')
        package_id = data.get('package_id')
        users_id = data.get('users_id')
        tests = data.get('tests', [])

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        #  patient_entry table update
        update_query = """
            UPDATE patient_entry
            SET cell=%s, patient_name=%s, father_hasband_MR=%s, age=%s, gender=%s,
                email=%s, address=%s, sample=%s, priority=%s, remarks=%s,
                discount=%s, paid=%s, total_fee=%s, company_id=%s,
                package_id=%s, users_id=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (
            cell, patient_name, father_hasband_MR, age, gender, email, address,
            sample, priority, remarks, discount, paid, total_fee,
            company_id, package_id, users_id, id
        ))

        #  test_profiles table update
        for test in tests:
            test_name = test.get('test_name')
            delivery_time = test.get('delivery_time')
            fee = test.get('fee')
            patient_test_id = test.get('patient_test_id')

            # pehle patient_tests se test_id nikalte hain
            cursor.execute("SELECT test_id FROM patient_tests WHERE id=%s", (patient_test_id,))
            test_row = cursor.fetchone()
            if test_row:
                test_id = test_row[0]
                print("test_id", test_id)
                cursor.execute("""
                    UPDATE test_profiles
                    SET test_name=%s, delivery_time=%s, fee=%s, sample_required = %s
                    WHERE id=%s
                """, (test_name,sample_required, delivery_time, fee, test_id))
                print("this is test_id", test_id)

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Patient entry aur test_profiles dono update ho gaye",
            "status": 200
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- Delete Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['DELETE'])
def delete_patient_entry(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM patient_entry WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry deleted successfully",
                        "status" : 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------------Test Verify ---------------------------------
@patient_entry_bp.route('/verify_test/<int:patient_test_id>', methods=['PATCH'])
def verify_test(patient_test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        update_query = """
            UPDATE patient_tests
            SET status = 'verified'
            WHERE id = %s
        """
        cursor.execute(update_query, (patient_test_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Test verified successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------------------- GET Unverifyed data --------------------
@patient_entry_bp.route('/unverified_tests', methods=['GET'])
def get_unverified_tests():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Optional: filter by patient_id
        patient_id = request.args.get('patient_id')

        if patient_id:
            query = "SELECT * FROM patient_tests WHERE patient_id = %s AND status = 'unverified'"
            cursor.execute(query, (patient_id,))
        else:
            query = "SELECT * FROM patient_tests WHERE status = 'unverified'"
            cursor.execute(query)

        results = cursor.fetchall()
        cursor.close()

        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------------------- Log Patient Activity ---------------------- #
@patient_entry_bp.route('/activity', methods=['POST'])
def log_patient_activity():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)  # DictCursor for easy column access

        data = request.get_json()
        patient_id = data.get('patient_id')
        activity = data.get('activity')

        # --- Validation ---
        if not patient_id or not activity:
            return jsonify({"error": "patient_id and activity are required"}), 400

        from datetime import datetime

        now_time = datetime.now()

        # --- Get last activity ---
        cursor.execute("""
            SELECT created_at 
            FROM patient_activity_log 
            WHERE patient_id = %s 
            ORDER BY id DESC LIMIT 1
        """, (patient_id,))
        last_record = cursor.fetchone()

        # --- Determine reference time for turnaround ---
        if last_record and last_record['created_at']:
            reference_time = last_record['created_at']
        else:
            # First activity → use patient_entry created_at
            cursor.execute("""
                SELECT created_at
                FROM patient_entry
                WHERE id = %s
                LIMIT 1
            """, (patient_id,))
            entry_record = cursor.fetchone()
            reference_time = entry_record['created_at'] if entry_record and entry_record['created_at'] else now_time

        # --- Calculate turnaround time ---
        turnaround_time = str(now_time - reference_time)

        # --- Insert new activity ---
        cursor.execute("""
            INSERT INTO patient_activity_log (patient_id, activity, turnaround_time, created_at)
            VALUES (%s, %s, %s, %s)
        """, (patient_id, activity, turnaround_time, now_time))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Activity logged successfully",
            "patient_id": patient_id,
            "activity": activity,
            "turnaround_time": turnaround_time
        }), 201

    except Exception as e:
        print("Error in log_patient_activity:", str(e))
        return jsonify({"error": str(e)}), 500

#---------------------- GET patient activiety ------------------
@patient_entry_bp.route('/activity/<int:patient_id>', methods=['GET'])
def get_patient_activity(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # --- Fetch all activities for this patient ---
        cursor.execute("""
            SELECT activity,  created_at
            FROM patient_activity_log
            WHERE patient_id = %s
            ORDER BY created_at ASC
        """, (patient_id,))
        activities = cursor.fetchall()

        cursor.close()

        return jsonify({
            "patient_id": patient_id,
            "activities": activities,
            "total_activities": len(activities)
        }), 200

    except Exception as e:
        print("Error in get_patient_activity:", str(e))
        return jsonify({"error": str(e)}), 500

    
