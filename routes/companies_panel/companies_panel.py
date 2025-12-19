import math
from flask import Blueprint, request, jsonify, current_app
import MySQLdb.cursors
from flask_mysqldb import MySQL
import time
from routes.authentication.authentication import token_required


companies_panel_bp = Blueprint('companies_panel', __name__, url_prefix='/api/companies_panel')
mysql = MySQL()

# ===================== Companies Panel CRUD Operations ===================== #

# --------------------- Companies Panel GET with Search + Pagination -------------------
@companies_panel_bp.route('/', methods=['GET'])
@token_required
def get_companies_panels():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 🔹 Query params
        company_name = request.args.get("company_name", "", type=str)
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        filters = []
        params = []

        # 🔹 Search filter
        if company_name:
            filters.append("company_name LIKE %s")
            params.append(f"%{company_name}%")

        # 🔹 Date filters
        if from_date and to_date:
            filters.append("DATE(created_at) BETWEEN %s AND %s")
            params.extend([from_date, to_date])
        elif from_date:
            filters.append("DATE(created_at) >= %s")
            params.append(from_date)
        elif to_date:
            filters.append("DATE(created_at) <= %s")
            params.append(to_date)

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        # 🔹 Base query
        base_query = f"SELECT * FROM companies_panel {where_clause}"

        # 🔹 Count total records
        count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS subquery"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()["total"]

        # 🔹 Pagination + order
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([record_per_page, offset])

        cursor.execute(base_query, params)
        company_panel = cursor.fetchall()

        end_time = time.time()
        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": company_panel,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTime": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# --------------------- Companies Panel Create -------------------
@companies_panel_bp.route('/', methods=['POST'])
@token_required
def create_companies_panel():
    start_time = time.time()
    
    data = request.get_json()
    company_name = data.get('company_name')
    head_name = data.get('head_name')
    contact_no = data.get('contact_no')
    user_name = data.get('user_name')
    age = data.get('age')


    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO companies_panel (company_name, head_name, contact_no, user_name, age, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            (company_name, head_name, contact_no, user_name, age)
        )
        mysql.connection.commit()
        end_time = time.time()
        return jsonify({"message": "Companies panel created successfully",
                        "status": 201,
                        "execution_time": end_time - start_time}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Update -------------------
@companies_panel_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_companies_panel(id):
    start_time = time.time()
    
    data = request.get_json()
    company_name = data.get('company_name')
    head_name = data.get('head_name')
    contact_no = data.get('contact_no')
    user_name = data.get('user_name')
    age = data.get('age')

    # type validation
    errors = []
    if not isinstance(company_name, str):
        errors.append("company_name must be a string")
    if not isinstance(head_name, str):
        errors.append("head_name must be a string")
    if not isinstance(user_name, str):
        errors.append("user_name must be a string")
    if not isinstance(age, int):
        errors.append("age must be an integer")
    if errors:
        return jsonify({"error": errors}), 400

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE companies_panel SET company_name=%s, head_name=%s, contact_no=%s, user_name=%s, age=%s WHERE id=%s",
            (company_name, head_name, contact_no, user_name, age, id)
        )
        mysql.connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        end_time = time.time()
        
        return jsonify({"message": "Companies panel updated successfully",
                        "status": 200,
                        "exection_time": end_time - start_time
                        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Delete -------------------
@companies_panel_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_companies_panel(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM companies_panel WHERE id=%s", (id,))
        mysql.connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        end_time = time.time()
        return jsonify({"message": "Companies panel deleted successfully",
                        "status": 200,
                        "execution_time" : end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# --------------------- Companies Panel get by id -------------------
@companies_panel_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_companies_panel(id):
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM companies_panel WHERE id=%s"
        cursor.execute(query,(id,))
        result = cursor.fetchone()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        end_time = time.time()

        return jsonify({"message": "Companies panel get successfully",
                        "status": 200,
                        "result": result,
                        "execution_time" : end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Get by ID with patient data -------------------
@companies_panel_bp.route('/company/<int:id>', methods=['GET'])
@token_required
def get_companies_panel_by_id(id):
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # filtertion
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        cursor.execute("SELECT * FROM companies_panel WHERE id=%s", (id,))
        company = cursor.fetchone()
        
        if not company:
            return jsonify({"error": "Company not found"}), 404

        counter_query = "SELECT pt_id, total_fee FROM counter WHERE company_id = %s"
        cursor.execute(counter_query,(id,))
        counter_data = cursor.fetchall()
        
        patients = []

        for row in counter_data:
            pt_id = row['pt_id']
            total_fee = row['total_fee']
            
            
            print("pr_id", pt_id)
        
            cursor.execute("""
                SELECT * FROM patient_entry 
                WHERE id=%s AND DATE(created_at) BETWEEN %s AND %s
            """, (pt_id, from_date, to_date))
            
            patient = cursor.fetchone()
            
            if patient:
                patient['total_fee'] = total_fee
                patients.append(patient)
            end_time = time.time()

            

        return jsonify({
            "company": company,
            "execution_time" : end_time - start_time,
            "patients": patients
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------------Company Search by Head Name-------------------
@companies_panel_bp.route('/search/<string:head_name>', methods=['GET'])
@token_required
def search_companies_panel_by_head_name(head_name):
    start_time = time.time()
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
                "age": row[5],
                "status": 200
            })
        end_time = time.time()
        # now execution time append to companies_panel
        for company in companies_panels:
            company['execution_time'] = end_time - start_time

        return jsonify(companies_panels), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
