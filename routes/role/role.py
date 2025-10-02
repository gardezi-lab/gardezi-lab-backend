import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL

role_bp = Blueprint('role', __name__, url_prefix='/api/role')
mysql = MySQL()

# ===================== Role Crud operations ===================== #

# --------------------- Get all roles (Search + Pagination) --------------------- #
@role_bp.route('/', methods=['GET'])
def get_roles():
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor(DictCursor)

        # Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM roles"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("role_name LIKE %s")
            values.append(f"%{search}%")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cur.execute(count_query, values)
        total_records = cur.fetchone()["total"]

        # Pagination + Order
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cur.execute(base_query, values)
        roles = cur.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": roles,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Get role by ID --------------------- #
@role_bp.route('/<int:role_id>', methods=['GET'])
def get_role(role_id):
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        role = cur.fetchone()
        cur.close()
        if role:
            return jsonify(role), 200
        else:
            return jsonify({"error": "Role not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Create a new role --------------------- #
@role_bp.route('/', methods=['POST'])
def create_role():
    try:
        data = request.get_json()
        role_name = data.get("role_name")
        if not role_name:
            return jsonify({"error": "Role name is required"}), 400
        if not isinstance(role_name, str):
            return jsonify({"error": "Role name must be a string"}), 400

        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO roles (role_name) VALUES (%s)", (role_name,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Update an existing role --------------------- #
@role_bp.route('/<int:role_id>', methods=['PUT'])
def update_role(role_id):
    try:
        data = request.get_json()
        role_name = data.get("role_name")
        if not role_name:
            return jsonify({"error": "Role name is required"}), 400
        if not isinstance(role_name, str):
            return jsonify({"error": "Role name must be a string"}), 400

        mysql = current_app.mysql
        cur = mysql.connection.cursor()

        # Check if role already exists with same name
        cur.execute("SELECT * FROM roles WHERE role_name = %s AND id != %s", (role_name, role_id))
        if cur.fetchone():
            return jsonify({"error": "Role already exists"}), 400

        # Check if role exists
        cur.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        existing_role = cur.fetchone()
        if not existing_role:
            return jsonify({"error": "Role not found"}), 404

        cur.execute("UPDATE roles SET role_name = %s WHERE id = %s", (role_name, role_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Delete a role --------------------- #
@role_bp.route('/<int:role_id>', methods=['DELETE'])
def delete_role(role_id):
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
