from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL
from flask import current_app 

department_bp = Blueprint('department', __name__, url_prefix='/api/department')
#-------------------Department CRUD Operations-------------------
mysql = MySQL()
#----------------Department GET -------------------
@department_bp.route('/', methods=['GET'])
def get_departments():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments")
        result = cursor.fetchall()
        #convert result to json
        departments = []
        for row in result:
            departments.append({
                "id": row[0],
                "department": row[1]
            })
        return jsonify(departments), 200
    except Exception as e:   
        return jsonify({"error": str(e)}), 500
#----------------Department Create -------------------
@department_bp.route('/', methods=['POST'])
def create_department():
    try:
        data = request.get_json()
        department = data.get('department')
        if department == "":
            return jsonify({"error": "Department name cannot be empty"}), 400
        # Check for duplicate department
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE department=%s", (department,))
        existing_department = cursor.fetchone()
        # Check if department is empty
        if existing_department:
            return jsonify({"error": "Department already exists"}), 400
        #check if department is a number
        if isinstance(department, int):
            return jsonify({"error": "Department name cannot be a number"}), 400
        
        cursor.execute("INSERT INTO departments (department) VALUES (%s)", (department,))
        mysql.connection.commit()
        return jsonify({"message": "Department created successfully"}), 201
    except Exception as e:   
        return jsonify({"error": str(e)}), 500
#----------------Department Update -------------------
@department_bp.route('/<int:id>', methods=['PUT'])
def update_department(id):
    try:
        data = request.get_json()
        department = data.get('department')
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
        return jsonify({"message": "Department updated successfully"}), 200
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
        return jsonify({"message": "Department deleted successfully"}), 200
    except Exception as e:   
        return jsonify({"error": str(e)}), 500
#----------------Department Get by ID -------------------
@department_bp.route('/<int:id>', methods=['GET'])
def get_department_by_id(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM departments WHERE id=%s", (id,))
        result = cursor.fetchone()
        #convert result to json
        if result:
            department = {
                "id": result[0],
                "department": result[1]
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
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, department FROM departments WHERE department LIKE %s", ('%' + name + '%',))
        
        result = cursor.fetchone()  # fetchall ke bajaye fetchone use karein
        
        if not result:
            return jsonify({"message": "No departments found"}), 404

        return jsonify({
            "id": result[0],
            "department": result[1]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

