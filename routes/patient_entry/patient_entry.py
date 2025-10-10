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
def create_patient_entry():
    try:
        data = request.get_json()

        # --- Extract Fields ---
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test = data.get('test', [])  # list of {"name": ..., "fee": ...}

        # --- Validations ---
        errors = []
        if not cell or not cell.isdigit() or len(cell) != 11:
            errors.append("Cell must be 11 digits.")
        if not patient_name or not str(patient_name).strip():
            errors.append("Patient name is required.")
        if age is None:
            errors.append("Age is required.")
        if not gender or not str(gender).strip():
            errors.append("Gender is required.")
        if not sample or not str(sample).strip():
            errors.append("Sample is required.")
        if not reffered_by or not str(reffered_by).strip():
            errors.append("Referred By is required.")

        if errors:
            return jsonify({"errors": errors}), 400

        age = str(age)

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # ---  Generate Unique MR Number ---
        prefix = "2025-GL-"
        while True:
            random_number = random.randint(1000, 9999)
            MR_number = f"{prefix}{random_number}".strip()
            cursor.execute("SELECT COUNT(*) AS count FROM patient_entry WHERE MR_number = %s", (MR_number,))
            result = cursor.fetchone()
            if result and result['count'] == 0:
                break  # Unique MR number found

        # ---  Insert into patient_entry (without entry_date) ---
        insert_query = """
            INSERT INTO patient_entry 
            (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender,
             email, address, package, sample, priority, remarks, MR_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            cell, patient_name, father_hasband_MR, age, company, reffered_by,
            gender, email, address, package, sample, priority, remarks,
            MR_number
        ))
        patient_id = cursor.lastrowid

        # ---  Insert Patient Tests ---
        total_fee = 0
        tests_list = []
        for test_obj in test:
            test_name = test_obj.get("name")
            fee = int(test_obj.get("fee", 0))

            cursor.execute(
                "SELECT id FROM test_profiles WHERE test_name = %s LIMIT 1",
                (test_name,)
            )
            row = cursor.fetchone()
            test_id = row['id'] if row else None

            if test_id:
                cursor.execute(
                    "INSERT INTO patient_tests (patient_id, test_id, verified) VALUES (%s, %s, %s)",
                    (patient_id, test_id, "Unverified")
                )
                patient_test_id = cursor.lastrowid
                tests_list.append({
                    "patient_test_id": patient_test_id,
                    "test_name": test_name,
                    "fee": fee
                })
                total_fee += fee
            else:
                tests_list.append({
                    "patient_test_id": None,
                    "test_name": test_name,
                    "fee": "Not Found"
                })

        # ---  Log Activity ---
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
            "tests": tests_list,
            "total_fee": total_fee
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
        cursor = mysql.connection.cursor(DictCursor)

        # Sirf un tests ko lao jin ka result patient_results me abhi tak add nahi hua
        query = """
        SELECT pt.id AS patient_test_id, tp.test_name
        FROM patient_tests pt
        JOIN test_profiles tp ON pt.test_id = tp.id
        WHERE pt.patient_id = %s
        AND pt.id NOT IN (
            SELECT DISTINCT patient_test_id FROM patient_results
        )
        """
        cursor.execute(query, (patient_id,))
        tests = cursor.fetchall()

        cursor.close()
        return jsonify(tests), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-------------------GET patient selected test parameters by patient_test_id----------
@patient_entry_bp.route('/test_parameters/<int:patient_test_id>/', methods=['GET'])
def get_test_parameters(patient_test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        query = """
        SELECT tp.parameter_name, tp.unit, tp.normalvalue, tp.default_value, tp.id AS parameter_id
        FROM parameters tp
        JOIN patient_tests pt ON tp.test_profile_id = pt.test_id
        WHERE pt.id = %s
        """
        cursor.execute(query, (patient_test_id,))
        parameters = cursor.fetchall()
        cursor.close()
        return jsonify(parameters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#----------------- Add result of patient selected test  by patient_test_id -------------
@patient_entry_bp.route('/test_results/<int:patient_test_id>/', methods=['POST'])
def save_test_results(patient_test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        data = request.get_json()
        patient_id = data.get('patient_id')
        parameters = data.get('parameters', [])

        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400

        # ✅ Step 1: Check if results already exist for this patient_test_id
        cursor.execute("""
            SELECT COUNT(*) AS result_count
            FROM patient_results
            WHERE patient_test_id = %s
        """, (patient_test_id,))
        result_check = cursor.fetchone()

        if result_check and result_check[0] > 0:
            cursor.close()
            return jsonify({
                "error": "Results for this test have already been added. You cannot add them again.",
                "status": "duplicate"
            }), 409  # 409 Conflict

        #  Step 2: Insert new results
        for item in parameters:
            cursor.execute("""
                INSERT INTO patient_results (patient_test_id, patient_id, parameter_id, result_value, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (patient_test_id, patient_id, item['parameter_id'], item['result_value']))

        #  Step 3: Mark this test as verified after results are added
        cursor.execute("""
            UPDATE patient_tests
            SET status = 'Verified', verified_at = NOW()
            WHERE id = %s AND patient_id = %s
        """, (patient_test_id, patient_id))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Results added successfully and test verified.",
            "patient_id": patient_id,
            "patient_test_id": patient_test_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Get All Patient Entries (Search + Pagination) ------------------ #
@patient_entry_bp.route('/', methods=['GET'])
def get_all_patient_entries():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # base query
        base_query = "SELECT * FROM patient_entry"
        where_clauses = []
        values = []

        if search:
            where_clauses.append(
                "(cell LIKE %s OR patient_name LIKE %s OR father_hasband_MR LIKE %s OR company LIKE %s OR reffered_by LIKE %s OR gender LIKE %s OR email LIKE %s OR address LIKE %s OR package LIKE %s OR sample LIKE %s OR priority LIKE %s OR remarks LIKE %s OR test LIKE %s)"
            )
            for _ in range(13):  # total searchable fields
                values.append(f"%{search}%")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # count total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cursor.execute(base_query, values)
        rows = cursor.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": rows,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Get Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['GET'])
def patient_get_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT * FROM patient_entry WHERE id = %s", (id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return jsonify({"patient_entry": row}), 200
            patient_entry = {
                "id": row[0],
                "cell": row[1],
                "patient_name": row[2],
                "father_hasband_MR": row[3],
                "age": row[4],
                "company": row[5],
                "reffered_by": row[6],
                "gender": row[7],
                "email": row[8],
                "address": row[9],
                "package": row[10],
                "sample": row[11],
                "priority": row[12],
                "remarks": row[13],
                "test": row[14],
                "status" : 200
            }
            return jsonify({"patient_entry": patient_entry}), 200
        return jsonify({"error": "Patient entry not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Update Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['PUT'])
def update_patient_entry(id):
    try:
        data = request.get_json()
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test = data.get('test')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        update_query = """
            UPDATE patient_entry
            SET cell=%s, patient_name=%s, father_hasband_MR=%s, age=%s, company=%s,
                reffered_by=%s, gender=%s, email=%s, address=%s, package=%s,
                sample=%s, priority=%s, remarks=%s, test=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test, id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry updated successfully",
                        "status": 200}), 200
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

    
