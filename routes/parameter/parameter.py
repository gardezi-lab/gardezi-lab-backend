import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL
import MySQLdb
import datetime
parameter_bp = Blueprint('parameter', __name__, url_prefix='/api/parameter')
mysql = MySQL()

# ===================== Parameter CRUD operations ===================== #

# --------------------- Get all parameters (Search + Pagination) --------------------- #
@parameter_bp.route('/', methods=['GET'])
def get_all_parameters():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM parameters"
        where_clauses = []
        values = []

        # Search condition
        if search:
            where_clauses.append(
                "(parameter_name LIKE %s OR sub_heading LIKE %s OR input_type LIKE %s OR unit LIKE %s)"
            )
            values.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        parameters = cursor.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": parameters,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------- Get parameter by ID --------------------- #
@parameter_bp.route('/<int:parameter_id>', methods=['GET'])
def get_parameter(parameter_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM parameters WHERE id = %s", (parameter_id,))
        parameter = cur.fetchone()
        cur.close()
        if parameter:
            return jsonify({
                "id": parameter[0],
                "parameter_name": parameter[1],
                "sub_heading": parameter[2],
                "input_type": parameter[3],
                "unit": parameter[4],
                "normal_value": parameter[5],
                "default_value": parameter[6],
                "dropdown_value": parameter[9],
                "status" : 200
            }), 200
        else:
            return jsonify({"error": "Parameter not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Create a new parameter --------------------- #
@parameter_bp.route('/<int:test_profile_id>', methods=['POST'])
def create_parameter(test_profile_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        data = request.get_json()

        parameter_name = data.get("parameter_name")
        sub_heading = data.get("sub_heading")
        input_type = data.get("input_type")
        unit = data.get("unit")
        normalvalue = data.get("normalvalue")
        default_value = data.get("default_value")
        dropdown_value = data.get("dropdown_value")
        
        

        # Check if test_profile_id exists
        cursor.execute("SELECT id FROM test_profiles WHERE id = %s", (test_profile_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Invalid test_profile_id"}), 400

        #  Check for duplicate parameter name within same test
        cursor.execute("""
            SELECT parameter_name FROM parameters 
            WHERE parameter_name = %s AND test_profile_id = %s
        """, (parameter_name, test_profile_id))
        if cursor.fetchone():
            return jsonify({
                "error": f"Parameter '{parameter_name}' already exists for this test. Please edit instead."
            }), 400

        #  Insert new parameter
        insert_query = """
            INSERT INTO parameters (
                parameter_name, sub_heading, input_type, unit,
                normalvalue, default_value, dropdown_values, test_profile_id
            )
            VALUES ( %s, %s, %s, %s, %s, %s, %s,%s)
        """
        cursor.execute(insert_query, (
            parameter_name, sub_heading, input_type, unit,
            normalvalue, default_value,dropdown_value,  test_profile_id
        ))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Parameter added successfully"}), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
#---------------------- GET parameter by test_profile_id --------
@parameter_bp.route('/test_parameters/<int:test_profile_id>', methods=['GET'])
def get_parameters(test_profile_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Check if test_profile_id exists
        cursor.execute("""
            SELECT id, test_name 
            FROM test_profiles 
            WHERE id = %s
        """, (test_profile_id,))
        test_profile = cursor.fetchone()

        if not test_profile:
            cursor.close()
            return jsonify({"error": "Invalid test_profile_id"}), 404

        #  Fetch ALL parameters for this test_profile_id
        query = """
            SELECT 
                id AS parameter_id,
                parameter_name,
                IFNULL(sub_heading, '') AS sub_heading,
                IFNULL(input_type, '') AS input_type,
                IFNULL(unit, '') AS unit,
                IFNULL(normalvalue, '') AS normalvalue,
                IFNULL(default_value, '') AS default_value,
                IFNULL(dropdown_values, '') AS dropdown_values,
                test_profile_id
            FROM parameters
            WHERE test_profile_id = %s
            ORDER BY id ASC
        """
        cursor.execute(query, (test_profile_id,))
        parameters = cursor.fetchall()
        cursor.close()

        #  If no data found
        if not parameters:
            return jsonify({
                "message": "No parameters found for this test profile",
                "test_profile": test_profile,
                "parameters": []
            }), 200

        #  Return list of parameters (not single object)
        return jsonify({
            "status": 200,
            "message": "Parameters fetched successfully",
            "test_profile": test_profile,
            "total_parameters": len(parameters),
            "parameters": parameters
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# --------------------- Update an existing parameter --------------------- #
@parameter_bp.route('/<int:parameter_id>', methods=['PUT'])
def update_parameter(parameter_id):
    try:
        data = request.get_json()

        parameter_name = data.get("parameter_name")
        sub_heading = data.get("sub_heading")
        input_type = data.get("input_type")
        unit = data.get("unit")
        normalvalue = data.get("normalvalue") or data.get("normal_value")  #  handle both
        default_value = data.get("default_value")
        dropdown_values = data.get("dropdown_values")
        

        
        # All must be strings
        if not all(isinstance(f, str) for f in [parameter_name, sub_heading, input_type, unit, normalvalue, default_value]):
            return jsonify({"error": "All fields must be strings"}), 400

        mysql = current_app.mysql
        cur = mysql.connection.cursor()

        #  Check if parameter exists
        cur.execute("SELECT id FROM parameters WHERE id = %s", (parameter_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Parameter with ID {parameter_id} not found"}), 404

        #  Update query
        update_query = """
            UPDATE parameters 
            SET parameter_name=%s, sub_heading=%s, input_type=%s, unit=%s, normalvalue=%s, default_value=%s,dropdown_values=%s 
            WHERE id=%s
        """
        cur.execute(update_query, (
            parameter_name, sub_heading, input_type, unit, normalvalue, default_value, dropdown_values,parameter_id
        ))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Parameter updated successfully", "status": 200}), 200

    except Exception as e:
        mysql = current_app.mysql
        mysql.connection.rollback()   
        return jsonify({"error": str(e)}), 500



# --------------------- Delete a parameter --------------------- #
@parameter_bp.route('/<int:parameter_id>', methods=['DELETE'])
def delete_parameter(parameter_id):
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM parameters WHERE id = %s", (parameter_id,))
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Parameter not found"}), 404

        cur.execute("DELETE FROM parameters WHERE id = %s", (parameter_id,))
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Parameter deleted successfully","status":200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    #-------------------parameter search by parameter name --------------------
@parameter_bp.route('/search/<string:parameter_name>', methods=['GET'])
def search_parameter(parameter_name):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM parameters WHERE parameter_name LIKE %s", ('%' + parameter_name + '%',))
        results = cur.fetchall()

        # Agar koi result nahi mila to not found ka response bhejo
        if not results:
            cur.close()
            return jsonify({"message": "Parameter not found"}), 404

        parameters = []
        for result in results:
            parameters.append({
                "id": result[0],
                "parameter_name": result[1],
                "sub_heading": result[2],
                "input_type": result[3],
                "unit": result[4],
                "normal_value": result[5],
                "default_value": result[6],
                "status" : 200
                
            })
        cur.close()
        return jsonify(parameters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------TODO parameters value ----------------
@parameter_bp.route('/dropdown_value', methods=['POST'])
def add_value():
    
    data = request.get_json()
    
    value = data.get('value')
    parameter_id = data.get('parameter_id')
    
    cursor = mysql.connection.cursor()
    
    insert_query = """
            INSERT INTO parameter_value (
                value,parameter_id,created_at
            )
            VALUES ( %s, %s, NOW())
        """
    cursor.execute(insert_query, (
            value,parameter_id))
    cursor.connection.commit()
    cursor.close()
    return jsonify({"message": 'value is added sucessfuly', "status": 201})
# -------------------TODO GET value by parameter-id --------------------
@parameter_bp.route('/dropdown_value/<int:parameter_id>', methods=['GET'])
def get_parameter_value(parameter_id):
    try:
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT id, parameter_id, value, created_at FROM parameter_value WHERE parameter_id = %s", (parameter_id,))
        rows = cur.fetchall()
        cur.close()

        # If no records found
        if not rows:
            return jsonify({
                "parameter_id": parameter_id,
                "dropdown_values": [],
                "status": 200
            }), 200
        
        dropdown_values = []
        for r in rows:
            r_copy = dict(r)
            r_copy.pop('parameter_id', None)
            dropdown_values.append(r_copy)

        return jsonify({
            "parameter_id": rows[0]['parameter_id'],
            "dropdown_values": dropdown_values,
            "status": 200
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- TODO DELETE parameter value parameter_id--------------
@parameter_bp.route('/dropdown_value/<int:id>', methods=['DELETE'])
def delete_parameter_value(id):
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM parameter_value WHERE id = %s", (id,))
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Parameter not found"}), 404

        cur.execute("DELETE FROM parameter_value WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Parameter deleted successfully","status":200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ----------------TODO UPDATE parameter value -----------------------
@parameter_bp.route('/value_update/<int:parameter_id>', methods=['PUT'])
def update_parameter_value(parameter_id):
    try:
        data = request.get_json()

        value = data.get("value")
        

        mysql = current_app.mysql
        cur = mysql.connection.cursor()

        #  Check if parameter exists
        cur.execute("SELECT id FROM parameter_value WHERE id = %s", (parameter_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Parameter with ID {parameter_id} not found"}), 404

        #  Update query
        update_query = """
            UPDATE parameter_value 
            SET value=%s
            WHERE id=%s
        """
        cur.execute(update_query, (
            value,parameter_id,
        ))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Parameter value updated successfully", "status": 200}), 200

    except Exception as e:
        mysql = current_app.mysql
        mysql.connection.rollback()   
        return jsonify({"error": str(e)}), 500