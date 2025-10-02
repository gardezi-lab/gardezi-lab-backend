import math
from flask import Blueprint, request, jsonify, current_app
import MySQLdb.cursors
from flask_mysqldb import MySQL

account_bp = Blueprint('account', __name__, url_prefix='/api/accounts')
mysql = MySQL()


# -------------------- GET with Search + Pagination -------------------- #
@account_bp.route('/', methods=['GET'])
def get_accountheads():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # base query
        base_query = "SELECT * FROM account_heads"
        where_clauses = []
        values = []

        if search:
            where_clauses.append(
                "(name_head LIKE %s OR head_code LIKE %s OR parent_account LIKE %s)"
            )
            values.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # total count
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # add pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        accounts = cursor.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": accounts,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:   
        return jsonify({"error": str(e)}), 500


# -------------------- POST -------------------- #
@account_bp.route('/', methods=['POST'])
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

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_heads WHERE name_head=%s", (name_head,))
        existing_head = cursor.fetchone()

        if existing_head:
            return jsonify({"error": "Head Name already exists"}), 400

        if name_head.isnumeric():
            return jsonify({"error": "Head Name cannot be a number"}), 400

        cursor.execute(
            "INSERT INTO account_heads (name_head, head_code, ob, ob_date, parent_account) VALUES (%s, %s, %s, %s, %s)",
            (name_head, head_code, ob, ob_date, parent_account,)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Account Head created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- PUT (Update) -------------------- #
@account_bp.route('/<int:id>', methods=['PUT'])
def update_account_head(id):
    try:
        data = request.get_json()
        name_head = data.get("name_head")
        head_code = data.get("head_code")
        ob = data.get("ob")
        ob_date = data.get("ob_date")
        parent_account = data.get("parent_account")
        
        if not isinstance(name_head, str) or not isinstance(head_code, str):
            return jsonify({"error": "Head name and code must be strings"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_heads WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Head not found"}), 404

        cursor.execute(
            """UPDATE account_heads 
               SET name_head = %s, head_code = %s, ob = %s, ob_date = %s, parent_account = %s 
               WHERE id = %s""",
            (name_head, head_code, ob, ob_date, parent_account, id)
        )
        mysql.connection.commit()
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
def delete_account_head(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM account_heads WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Account Head not found"}), 404

        cursor.execute("DELETE FROM account_heads WHERE id=%s", (id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Account Head deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET by ID -------------------- #
@account_bp.route('/<int:id>', methods=['GET'])
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
