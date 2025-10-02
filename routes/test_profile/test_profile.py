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
        test_name = data.get("test_name")
        test_code = data.get("test_code")
        sample_required = data.get("sample_required")
        select_header = data.get("select_header")
        fee = data.get("fee")
        delivery_time = data.get("delivery_time")
        serology_elisa = data.get("serology_elisa")
        interpretation = data.get("interpretation")

        # validation
        if not all([test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation]):
            return jsonify({"error": "All fields are required"}), 400
        if not all(isinstance(f, str) for f in [test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation]):
            return jsonify({"error": "All fields must be strings"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        insert_query = """
            INSERT INTO test_profiles (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation)) 
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            "message": "Test Profile created successfully",
            "id": new_id,
            "test_name": test_name,
            "test_code": test_code,
            "sample_required": sample_required,
            "select_header": select_header,
            "fee": fee,
            "delivery_time": delivery_time,
            "serology_elisa": serology_elisa,
            "interpretation": interpretation
        }), 201

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
        return jsonify({"message": "Test Profile deleted successfully"}), 200

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
