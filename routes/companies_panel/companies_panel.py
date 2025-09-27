from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL


companies_panel_bp = Blueprint('companies_panel', __name__, url_prefix='/api/companies_panel')
mysql = MySQL()

#=====================Companies Panel CRUD Operations=====================
#---------------------Companies Panel GET  With validation ------------------- 
@companies_panel_bp.route('/', methods=['GET'])
def get_companies_panels():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM companies_panel")
        result = cursor.fetchall()
        #convert result to json
        companies_panels = []
        for row in result:
            companies_panels.append({
                "id": row[0],
                "company_name": row[1],
                "head_name": row[2],
                "contact_no": row[3],
                "user_name": row[4],
                "age": row[5]
            })
        return jsonify(companies_panels), 200
    except Exception as e:   
        return jsonify({"error": str(e)}), 500
#---------------------Companies Panel Create  With validation -------------------
@companies_panel_bp.route('/', methods=['POST'])
def create_companies_panel():
    data = request.get_json()
    company_name = data.get('company_name')
    head_name = data.get('head_name')
    contact_no = data.get('contact_no')
    user_name = data.get('user_name')
    age = data.get('age')
    
    #add validatin these are all required fields
    if not company_name or not head_name or not contact_no or not user_name or not age:
        return jsonify({"error": "All fields are required"}), 400
    #add validation company_name, head_name, user_name should be string and age should be integer
    if not isinstance(company_name, str) or not isinstance(head_name, str) or not isinstance(user_name, str) or not isinstance(age, int):
        # show error with how at which field with feilds name the error is
        errors = []
        if not isinstance(company_name, str):
            errors.append("company_name must be a string")
        if not isinstance(head_name, str):
            errors.append("head_name must be a string")
        if not isinstance(user_name, str):
            errors.append("user_name must be a string")
        if not isinstance(age, int):
            errors.append("age must be an integer")
        return jsonify({"error": errors}), 400
    # Validate the incoming data
    if not data or 'company_name' not in data or 'head_name' not in data:
        return jsonify({"error": "Invalid input"}), 400
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO companies_panel (company_name, head_name, contact_no, user_name, age) VALUES (%s, %s, %s, %s, %s)",
                       (data['company_name'], data['head_name'], data['contact_no'], data['user_name'], data['age']))
        mysql.connection.commit()
        return jsonify({"message": "Companies panel created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#---------------------Companies Panel Update  With validation -------------------
@companies_panel_bp.route('/<int:id>', methods=['PUT'])
def update_companies_panel(id):
    data = request.get_json()
    company_name = data.get('company_name')
    head_name = data.get('head_name')
    contact_no = data.get('contact_no')
    user_name = data.get('user_name')
    age = data.get('age')
    #show error which feild are with there name 
    if not isinstance(company_name, str) or not isinstance(head_name, str) or not isinstance(user_name, str) or not isinstance(age, int):
        # show error with how at which field with feilds name the error is
        errors = []
        if not isinstance(company_name, str):
            errors.append("company_name must be a string")
        if not isinstance(head_name, str):
            errors.append("head_name must be a string")
        if not isinstance(user_name, str):
            errors.append("user_name must be a string")
        if not isinstance(age, int):
            errors.append("age must be an integer")
        return jsonify({"error": errors}), 400
    
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE companies_panel SET company_name=%s, head_name=%s, contact_no=%s, user_name=%s, age=%s WHERE id=%s",
                       (data.get('company_name'), data.get('head_name'), data.get('contact_no'), data.get('user_name'), data.get('age'), id))
        mysql.connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        return jsonify({"message": "Companies panel updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#---------------------Companies Panel Delete  With validation -------------------
@companies_panel_bp.route('/<int:id>', methods=['DELETE'])
def delete_companies_panel(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM companies_panel WHERE id=%s", (id,))
        mysql.connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        return jsonify({"message": "Companies panel deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Companies Panel Get by ID  With validation -------------------
@companies_panel_bp.route('/<int:id>', methods=['GET'])
def get_companies_panel_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM companies_panel WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Companies panel not found"}), 404
        companies_panel = {
            "id": result[0],
            "company_name": result[1],
            "head_name": result[2],
            "contact_no": result[3],
            "user_name": result[4],
            "age": result[5]
        }
        return jsonify(companies_panel), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------------Company Search by Head Name-------------------
@companies_panel_bp.route('/search/<string:head_name>', methods=['GET'])
def search_companies_panel_by_head_name(head_name):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM companies_panel WHERE head_name LIKE %s", ('%' + head_name + '%',))
        result = cursor.fetchall()
        companies_panels = []
        for row in result:
            companies_panels.append({
                "id": row[0],
                "company_name": row[1],
                "head_name": row[2],
                "contact_no": row[3],
                "user_name": row[4],
                "age": row[5]
            })
        return jsonify(companies_panels), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
    
    
#------------------------Create the company table creation query for mysql----------------
# Create Table companies_panel (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     company_name VARCHAR(100) NOT NULL,
#     head_name VARCHAR(100) NOT NULL,
#     contact_no VARCHAR(15),
#     user_name VARCHAR(50),
#     age INT
# );