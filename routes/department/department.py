from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL
import MySQLdb.cursors
import math
import time
import pandas as pd

department_bp = Blueprint('department', __name__, url_prefix='/api/department')
mysql = MySQL()

# ---------------- Department GET ------------------- #
@department_bp.route('/', methods=['GET'])
def get_departments_optimized():
    start_time = time.time()
    try:
        mysql = current_app.mysql  # type: ignore
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        sql = "SELECT SQL_CALC_FOUND_ROWS id, department_name FROM departments"
        values = []

        if search:
            sql += " WHERE department_name LIKE %s"
            values.append(f"%{search}%")

        sql += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(sql, values)
        rows = cursor.fetchall()

        # Use pandas for vectorized transformation
        df = pd.DataFrame(rows)
        formatted_departments = df.to_dict(orient='records')

        # get total records in same session
        cursor.execute("SELECT FOUND_ROWS() as total")
        total_records = cursor.fetchone()['total']
        total_pages = math.ceil(total_records / record_per_page)

        end_time = time.time()
        execution_time_ms = round((end_time - start_time) * 1000, 2)

        return jsonify({
            "data": formatted_departments,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTimeMs": execution_time_ms
        }), 200

    except Exception as e:
        end_time = time.time()
        execution_time_ms = round((end_time - start_time) * 1000, 2)
        return jsonify({
            "error": str(e),
            "executionTimeMs": execution_time_ms
        }), 500


# ---------------- Department Create ------------------- #
@department_bp.route('/', methods=['POST'])
def create_department():
    try:
        data = request.get_json(force=False)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        department_name = data.get('department_name')
        if not department_name or department_name.strip() == "":
            return jsonify({"error": "Department name cannot be empty"}), 400
        # Check for duplicate department
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM departments WHERE department=%s", (department_name,))
        existing_department = cursor.fetchone()
        if existing_department:
            return jsonify({"error": "Department already exists"}), 400

        # Check if department is a number
        if isinstance(department_name, int):
            return jsonify({"error": "Department name cannot be a number"}), 400

        cursor.execute("INSERT INTO departments (department_name) VALUES (%s)", (department_name,))
        mysql.connection.commit() # type: ignore
        cursor.close()
        return jsonify({"message": "Department created successfully",
                        "status": 201}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- Department Update ------------------- #
@department_bp.route('/<int:id>', methods=['PUT'])
def update_department(id):
    try:
        data = request.get_json()
        department_name = data.get('department_name')

        if not department_name or department_name.strip() == "":
            return jsonify({"error": "Department name cannot be empty"}), 400

        if isinstance(department_name, int):
            return jsonify({"error": "Department name cannot be a number"}), 400
        #check if department is already exists
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM departments WHERE department_name=%s", (department_name,))
        existing_department = cursor.fetchone()
        if existing_department:
            return jsonify({"error": "Department already exists"}), 400
        cursor.execute("UPDATE departments SET department_name=%s WHERE id=%s", (department_name, id))
        mysql.connection.commit() # type: ignore
        cursor.close()
        return jsonify({"message": "Department updated successfully",
                        "status": 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- Department Delete ------------------- #
@department_bp.route('/<int:id>', methods=['DELETE'])
def delete_department(id):
    try:
        #if department id is not in database then return error
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM departments WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Department not found"}), 404
        
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("DELETE FROM departments WHERE id=%s", (id,))
        mysql.connection.commit() # type: ignore
        cursor.close()
        return jsonify({"message": "Department deleted successfully",
                        "status" : 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- Department Get by ID ------------------- #
@department_bp.route('/<int:id>', methods=['GET'])
def get_department_by_id(id):
    try:
        mysql = current_app.mysql # type: ignore
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE id=%s", (id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            department = {
                "id": result[0],
                "department_name": result[1],
                "status": 200
            }
            return jsonify(department), 200
        else:
            return jsonify({"message": "Department not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- Department Search by Name ------------------- #
@department_bp.route('/search/<string:name>', methods=['GET'])
def search_departments(name):
    try:
        mysql = current_app.mysql # type: ignore
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, department_name FROM departments WHERE department_name LIKE %s",
            ('%' + name + '%',)
        )
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "No departments found"}), 404

        return jsonify({
            "id": result[0],
            "department": result[1],
            "status": 200
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
