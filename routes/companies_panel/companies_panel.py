import math
from flask import Blueprint, request, jsonify, current_app
import MySQLdb.cursors
from flask_mysqldb import MySQL

companies_panel_bp = Blueprint('companies_panel', __name__, url_prefix='/api/companies_panel')
mysql = MySQL()

# ===================== Companies Panel CRUD Operations ===================== #

# --------------------- Companies Panel GET with Search + Pagination -------------------
@companies_panel_bp.route('/', methods=['GET'])
def get_companies_panels():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # query params
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        
        filters = []
        params = []
        
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
        
        # base query
        base_query = f"SELECT * FROM companies_panel {where_clause}"
        
        cursor.execute(base_query,params)
        company_panel = cursor.fetchall()
        
        return jsonify({
            "data": company_panel,
            "status": 200
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Create -------------------
@companies_panel_bp.route('/', methods=['POST'])
def create_companies_panel():
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
        return jsonify({"message": "Companies panel created successfully",
                        "status": 201}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Update -------------------
@companies_panel_bp.route('/<int:id>', methods=['PUT'])
def update_companies_panel(id):
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
        return jsonify({"message": "Companies panel updated successfully",
                        "status": 200
                        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Delete -------------------
@companies_panel_bp.route('/<int:id>', methods=['DELETE'])
def delete_companies_panel(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM companies_panel WHERE id=%s", (id,))
        mysql.connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Companies panel not found"}), 404
        return jsonify({"message": "Companies panel deleted successfully",
                        "status": 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Companies Panel Get by ID -------------------
@companies_panel_bp.route('/<int:id>', methods=['GET'])
def get_companies_panel_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM companies_panel WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Companies panel not found"}), 404
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        companies_panel = {
            "id": result[0],
            "company_name": result[1],
            "head_name": result[2],
            "contact_no": result[3],
            "user_name": result[4],
            "age": result[5],
            "status": 200
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
                "age": row[5],
                "status": 200
            })
        return jsonify(companies_panels), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
