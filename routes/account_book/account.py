import math
from flask import Blueprint, request, jsonify, current_app
from routes.authentication.authentication import token_required
import MySQLdb.cursors
from flask_mysqldb import MySQL

account_bp = Blueprint('account', __name__, url_prefix='/api/accounts')
mysql = MySQL()


# -------------------- GET with Search + Pagination -------------------- #
@account_bp.route('/', methods=['GET'])
@token_required
def get_accountheads():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        base_query = "SELECT * FROM account_heads"
        where_clauses = ["trash = 0"]   
        values = []

        if search:
            where_clauses.append("(name_head LIKE %s OR head_code LIKE %s)")
            values.extend([f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # -------- Total Count -------- #
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) AS subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # -------- Pagination -------- #
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cursor.execute(base_query, values)
        users = cursor.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": users,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



        # accountheads = []
        # for row in result:
        #     accountheads.append({
        #         "id": row[0],              #  id add kar diya
        #         "head_name": row[1],
        #         "head_code": row[2],
        #         "ob": row[3],
        #         "ob_date": row[4],
        #         "parent_account": row[5],
        #         "created_at": row[6]
        #     })
        # return jsonify(accountheads), 200
    except Exception as e:   
        return jsonify({"error": str(e)}), 500


@account_bp.route('/', methods=['POST'])
@token_required
def create_accounthead():
    try:
        mysql = current_app.mysql
        data = request.get_json(force=False)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        name_head = data.get('name_head')
        head_code = data.get('head_code')
        ob = data.get('ob')
        ob_date = data.get('ob_date')
        parent_account = data.get('parent_account')

        if not name_head or name_head.strip() == "":
            return jsonify({"error": "Head name cannot be empty"}), 400
        # Check for duplicate department
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM account_heads WHERE name_head=%s", (name_head,))
        existing_department = cursor.fetchone()
        # Check if department is empty
        if existing_department:
            return jsonify({"error": "Head Name already exists"}), 400
        #check if department is a number
        if isinstance(name_head, int):
            return jsonify({"error": "Head Name name cannot be a number"}), 400
        
        cursor.execute("INSERT INTO account_heads (name_head, head_code, ob, ob_date, parent_account) VALUES (%s, %s, %s, %s, %s)", (name_head, head_code, ob, ob_date, parent_account))
        mysql.connection.commit() # type: ignore
        cursor.close()

        return jsonify({"message": "Account Head created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@account_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_account_by_id(id):
    try:
        mysql = current_app.mysql # type: ignore
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM account_heads WHERE id=%s", (id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            department = {
                "id": result[0],
                "name_head": result[1]
            }
            return jsonify(department), 200
        else:
            return jsonify({"message": "Head Name not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@account_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_head(id): 
    try:
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM account_heads WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Head not found"}), 404
        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("DELETE FROM account_heads WHERE id=%s", (id,))
        mysql.connection.commit() # type: ignore
        cursor.close()
        return jsonify({"message": "Head deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- PUT (Update) -------------------- #
@account_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_account_head(id):
    try:
        data = request.get_json()
        name_head = data.get("name_head")
        head_code = data.get("head_code")
        ob = data.get("ob")
        ob_date = data.get("ob_date")
        parent_account = data.get("parent_account")
        
        # if not isinstance(name_head, str) or not isinstance(head_code, str) :
        #     return jsonify({"error": "All fields must be strings"}), 400

        cursor = mysql.connection.cursor() # type: ignore
        cursor.execute("SELECT * FROM account_heads WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Head not found"}), 404

        update_query = """UPDATE account_heads 
                          SET name_head = %s, head_code = %s, ob = %s, ob_date = %s, parent_account = %s WHERE id = %s"""
        cursor.execute(update_query, (name_head, head_code, ob, ob_date, parent_account,  id))
        mysql.connection.commit() # type: ignore
        cursor.close()

        return jsonify({
            "message": "Head updated successfully",
            "id": id,
            "name_head": name_head,
            "head_code": head_code,
            "ob": ob,
            "ob_date": ob_date,
            "parent_account": parent_account
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- DELETE -------------------- #
@account_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_account_head(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute(
            "SELECT id FROM account_heads WHERE id = %s AND trash = 0",
            (id,)
        )
        result = cursor.fetchone()
        if not result:
            cursor.close()
            return jsonify({"error": "Account Head not found"}), 404

        cursor.execute(
            "UPDATE account_heads SET trash = 1 WHERE id = %s",
            (id,)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Account Head deleted successfully",
            "status": 200
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET by ID -------------------- #
@account_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_account_head_by_id(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_heads WHERE id=%s", (id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return jsonify(result), 200
        else:
            return jsonify({"error": "Account Head not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    