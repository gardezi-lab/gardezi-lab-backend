import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL

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
                "status" : 200
                
                
            }), 200
        else:
            return jsonify({"error": "Parameter not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Create a new parameter --------------------- #
@parameter_bp.route('/', methods=['POST'])
def create_parameter():
    try:
        data = request.get_json()
        parameter_name = data.get("parameter_name")
        sub_heading = data.get("sub_heading")
        input_type = data.get("input_type")
        unit = data.get("unit")
        normalvalue = data.get("normalvalue")
        default_value = data.get("default_value")

        # all fields are mandatory
        if not all([parameter_name, sub_heading, input_type, unit, normalvalue, default_value]):
            return jsonify({"error": "All fields are required"}), 400

        # all fields must be strings
        if not all(isinstance(f, str) for f in [parameter_name, sub_heading, input_type, unit, normalvalue, default_value]):
            return jsonify({"error": "All fields must be strings"}), 400

        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO parameters (parameter_name, sub_heading, input_type, unit, normalvalue, default_value) VALUES (%s, %s, %s, %s, %s, %s)",
            (parameter_name, sub_heading, input_type, unit, normalvalue, default_value)
        )
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Parameter created successfully",
                        "status" : 201}), 201
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
        normal_value = data.get("normal_value") or data.get("normalvalue")
        default_value = data.get("default_value")

        # Check if all fields are provided
        if not all([parameter_name, sub_heading, input_type, unit, normal_value, default_value]):
            return jsonify({"error": "All fields are required"}), 400

        if not all(isinstance(f, str) for f in [parameter_name, sub_heading, input_type, unit, normal_value, default_value]):
            return jsonify({"error": "All fields must be strings"}), 400

        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE parameters 
            SET parameter_name=%s, sub_heading=%s, input_type=%s, unit=%s, normalvalue=%s, default_value=%s 
            WHERE id=%s
        """, (parameter_name, sub_heading, input_type, unit, normal_value, default_value, parameter_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Parameter updated successfully","status" : 200}), 200

    except Exception as e:
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

    
