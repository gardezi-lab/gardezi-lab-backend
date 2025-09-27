from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

test_profile_bp = Blueprint('test_profile', __name__, url_prefix='/api/test_profile')
mysql = MySQL()


#-----------test&profile Crud operations---------------------#
#---------------------Get all test&profiles---------------------#
@test_profile_bp.route('/', methods=['GET'])
def get_all_test_profiles():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles")
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        test_profiles = [dict(zip(column_names, row)) for row in rows]
        return jsonify(test_profiles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Get test&profile by ID---------------------#
@test_profile_bp.route('/<int:test_profile_id>', methods=['GET'])
def get_test_profile(test_profile_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Test&Profile not found"}), 404
        column_names = [desc[0] for desc in cursor.description]
        return jsonify(dict(zip(column_names, row))), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Create a new test&profile---------------------#
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

        #  Check if all fields are provided
        if not all([test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation]):
            return jsonify({"error": "All fields are required"}), 400

        # Check that test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation are strings
        if not isinstance(test_name, str) or not isinstance(test_code, str) or not isinstance(sample_required, str) or not isinstance(select_header, str) or not isinstance(fee, str) or not isinstance(delivery_time, str) or not isinstance(serology_elisa, str) or not isinstance(interpretation, str):
            return jsonify({"error": "All fields must be strings"}), 400

        # Insert into DB
        cursor = mysql.connection.cursor()
        insert_query = """INSERT INTO test_profiles (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(insert_query, (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation)) 
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Test&Profile created successfully",
                        "id" : cursor.lastrowid,
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
#---------------------Update a test&profile---------------------#
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

        # Check that test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation are strings
        if not isinstance(test_name, str) or not isinstance(test_code, str) or not isinstance(sample_required, str) or not isinstance(select_header, str) or not isinstance(fee, str) or not isinstance(delivery_time, str) or not isinstance(serology_elisa, str) or not isinstance(interpretation, str):
            return jsonify({"error": "All fields must be strings"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Test&Profile not found"}), 404

        update_query = """UPDATE test_profiles 
                          SET test_name = %s, test_code = %s, sample_required = %s, select_header = %s, fee = %s, delivery_time = %s, serology_elisa = %s, interpretation = %s 
                          WHERE id = %s"""
        cursor.execute(update_query, (test_name, test_code, sample_required, select_header, fee, delivery_time, serology_elisa, interpretation, test_profile_id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Test&Profile updated successfully",
                        "test_name": test_name,
                        "test_code": test_code,
                        "sample_required": sample_required,
                        "select_header": select_header,
                        "fee": fee,
                        "delivery_time": delivery_time,
                        "serology_elisa": serology_elisa,
                        "interpretation": interpretation
                        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Delete a test&profile---------------------#
@test_profile_bp.route('/<int:test_profile_id>', methods=['DELETE'])
def delete_test_profile(test_profile_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM test_profiles WHERE id = %s", (test_profile_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Test&Profile not found"}), 404

        cursor.execute("DELETE FROM test_profiles WHERE id = %s", (test_profile_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Test&Profile deleted successfully"}), 200

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

        return jsonify({"test_profiles": rows}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
#-------------------- Get department names for select header ---------------------#
@test_profile_bp.route('/departments', methods=['GET'])
def get_departments():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT department_name FROM departments")  # ✅ correct column name
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        departments = [dict(zip(column_names, row)) for row in rows]
        cursor.close()
        return jsonify(departments), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
