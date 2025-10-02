from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL
import MySQLdb.cursors
import math

department_bp = Blueprint('department', __name__, url_prefix='/api/department')
mysql = MySQL()

# ---------------- Department GET ------------------- #
@department_bp.route('', methods=['GET'])
def get_departments():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # ✅ DictCursor use karo

        # Query params from frontend
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM departments"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("department_name LIKE %s")
            values.append(f"%{search}%")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # ✅ Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # ✅ Add pagination to main query
        base_query += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        departments = cursor.fetchall()
        #
        # ✅ Transform data into custom format
        formatted_departments = [
            {
                "id": dept["id"],  # db column "id"
                "department_name": dept["department"]  # db column "department_name"
            }
            for dept in departments
        ]

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": formatted_departments,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#----------------Department Create -------------------
@department_bp.route('/', methods=['POST'])
def create_department():
    try:
        data = request.get_json(force=False)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        department_name = data.get('department_name')
        if department_name == "":
            return jsonify({"error": "Department name cannot be empty"}), 400
        # Check for duplicate department
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE department=%s", (department_name,))
        existing_department = cursor.fetchone()
        # Check if department is empty
        if existing_department:
            return jsonify({"error": "Department already exists"}), 400
        #check if department is a number
        if isinstance(department_name, int):
            return jsonify({"error": "Department name cannot be a number"}), 400

        cursor.execute("INSERT INTO departments (department) VALUES (%s)", (department_name,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Department created successfully",
                        "status": 201}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#----------------Department Update -------------------
@department_bp.route('/<int:id>', methods=['PUT'])
def update_department(id):
    try:
        data = request.get_json()
        department = data.get('department_name')
        #check if department is number
        if isinstance(department,int):
            return jsonify({"error": "Department name cannot be a number"}), 400
        #check if department is already exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE department=%s", (department,))
        existing_department = cursor.fetchone()
        if existing_department:
            return jsonify({"error": "Department already exists"}), 400
        cursor.execute("UPDATE departments SET department=%s WHERE id=%s", (department, id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Department updated successfully",
                        "status": 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#----------------Department Delete -------------------
@department_bp.route('/<int:id>', methods=['DELETE'])
def delete_department(id): 
    try:
        #if department id is not in database then return error
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Department not found"}), 404
        
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM departments WHERE id=%s", (id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Department deleted successfully",
                        "status" : 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#----------------Department Get by ID -------------------
@department_bp.route('/<int:id>', methods=['GET'])
def get_department_by_id(id):
    try:
        mysql = current_app.mysql
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

#----------------Department Search by Name -------------------
@department_bp.route('/search/<string:name>', methods=['GET'])
def search_departments(name):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, department_name FROM departments WHERE department_name LIKE %s", ('%' + name + '%',))
        
        result = cursor.fetchone()  
        
        if not result:
            return jsonify({"message": "NO departments found"}), 404

        return jsonify({
            "id": result[0],
            "department": result[1],
            "status": 200
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

