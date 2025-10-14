import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL

test_profile_bp = Blueprint('test_profile', __name__, url_prefix='/api/test_profile')
mysql = MySQL()

# ===================== Test Profile CRUD operations ===================== #

# --------------------- Get all test profiles (Search + Pagination) --------------------- #
@test_profile_bp.route('/', methods=['GET'])
def get_all_test_profiles():
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor(DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # base query
        base_query = "SELECT * FROM test_profiles"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("test_name LIKE %s")
            values.append(f"%{search}%")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cur.execute(count_query, values)
        total_records = cur.fetchone()["total"]

        # pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cur.execute(base_query, values)
        test_profiles = cur.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": test_profiles,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Get test profile by ID --------------------- #
@test_profile_bp.route('/<int:test_profile_id>', methods=['GET'])
def get_test_profile(test_profile_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return jsonify({"error": "Test Profile not found"}), 404

        return jsonify(row), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Create a new test profile --------------------- #

@test_profile_bp.route('/', methods=['POST'])
def create_test_profile():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Basic fields ---
        test_name = data.get("test_name")
        fee = data.get("fee")
        department_id = data.get("department_id")  #  Now using department_id directly

        test_code = data.get("test_code")
        sample_required = data.get("sample_required")
        select_header = data.get("select_header")
        delivery_time = data.get("delivery_time")
        interpretation = data.get("interpretation")

        # --- Required fields validation ---
        required_fields = {
            "test_name": test_name,
            "fee": fee,
            "department_id": department_id
        }

        for field_name, value in required_fields.items():
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return jsonify({"error": f"Field '{field_name}' is required"}), 400

        # --- Boolean fields validation ---
        def to_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ['true', '1', 'yes', 'y']
            if isinstance(val, int):
                return val == 1
            return False

        if data.get("serology_elisa") is None:
            return jsonify({"error": "Field 'serology_elisa' is required"}), 400
        if data.get("unit_ref_range") is None:
            return jsonify({"error": "Field 'unit_ref_range' is required"}), 400
        if data.get("test_formate") is None:
            return jsonify({"error": "Field 'test_formate' is required"}), 400

        serology_elisa = to_bool(data.get("serology_elisa"))
        unit_ref_range = to_bool(data.get("unit_ref_range"))
        test_formate = to_bool(data.get("test_formate"))

        # --- Check if department_id is valid ---
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT id FROM departments WHERE id = %s LIMIT 1", (department_id,))
        dept_row = cursor.fetchone()
        if not dept_row:
            return jsonify({"error": f"Department with ID '{department_id}' not found"}), 400

        # --- Insert into test_profiles ---
        insert_query = """
            INSERT INTO test_profiles 
            (test_name, test_code, sample_required, select_header, fee, delivery_time,
             serology_elisa, interpretation, unit_ref_range, test_formate, department_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            test_name, test_code, sample_required, select_header, fee, delivery_time,
            serology_elisa, interpretation, unit_ref_range, test_formate, department_id
        ))
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Test Profile created successfully",
            "status": 201
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#---------------------- api for unique test code ------------------
@test_profile_bp.route('/check_test_code', methods=['POST'])
def check_test_code():
    try:
        data = request.get_json()
        test_code = data.get("test_code")

        if not test_code:
            return jsonify({"error": "test_code is required"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        # check if test_code exists
        query = "SELECT id FROM test_profiles WHERE test_code = %s"
        cursor.execute(query, (test_code,))
        existing = cursor.fetchone()
        cursor.close()

        if existing:
            return jsonify({
                "unique": False,
                "message": f"Test code '{test_code}' already exists."
            }), 200
        else:
            return jsonify({
                "unique": True,
                "message": f"Test code '{test_code}' is available."
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Update a test profile --------------------- #
@test_profile_bp.route('/<int:test_profile_id>', methods=['PUT'])
def update_test_profile(test_profile_id):
    try:
        data = request.get_json()
        test_name = data.get("test_name")
        test_code = data.get("test_code")
        sample_required = data.get("sample_required")
        select_header = data.get("select_header")
        fee = data.get("fee")
        delivery_time = data.get("delivery_time")
        serology_elisa = data.get("serology_elisa")
        interpretation = data.get("interpretation")

        if not all(isinstance(f, str) for f in [test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation]):
            return jsonify({"error": "All fields must be strings"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Test Profile not found"}), 404

        update_query = """
            UPDATE test_profiles 
            SET test_name = %s, test_code = %s, sample_required = %s, select_header = %s, fee = %s, delivery_time = %s, serology_elisa = %s, interpretation = %s 
            WHERE id = %s
        """
        cursor.execute(update_query, (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation, test_profile_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Test Profile updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Delete a test profile --------------------- #
@test_profile_bp.route('/<int:test_profile_id>', methods=['DELETE'])
def delete_test_profile(test_profile_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Test Profile not found"}), 404

        cursor.execute("DELETE FROM test_profiles WHERE id = %s", (test_profile_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Test&Profile deleted successfully","status" : 200}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#--------------------Search test&profile by test_name---------------------#
@test_profile_bp.route('/search/<string:test_name>', methods=['GET'])
def search_test_profile(test_name):
    try:
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM test_profiles WHERE test_name LIKE %s"
        cursor.execute(query, ("%" + test_name + "%",))
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return jsonify({"error": "No Test&Profile found"}), 404

        return jsonify({"test_profiles": rows,"status": 200}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Get department names for select header --------------------- #
@test_profile_bp.route('/departments', methods=['GET'])
def get_departments():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT department_name FROM departments")
        rows = cursor.fetchall()
        cursor.close()
        return jsonify(rows), 200
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- GET all tests of patient ------------------------
import MySQLdb

# --- GET API: Get patient test_profile by patient_id ---
import MySQLdb
from flask import jsonify 
@test_profile_bp.route('/patient_tests/<int:patient_id>/', methods=['GET'])
def get_patient_test_profile(patient_id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if patient exists
        cursor.execute("SELECT * FROM patient_tests WHERE patient_id = %s", (patient_id,))
        records = cursor.fetchall()

        if not records:
            return jsonify({"error": "Patient not found"}), 404

        # Prepare response (since multiple tests can belong to one patient)
        response = {
            "patient_id": patient_id,
            "tests": records  # return full list of test rows
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500