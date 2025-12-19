import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL
import time
from routes.authentication.authentication import token_required


role_bp = Blueprint('role', __name__, url_prefix='/api/role')
mysql = MySQL()

# ===================== Role Crud operations ===================== #

# --------------------- Get all roles (Search + Pagination) --------------------- #
@role_bp.route('/', methods=['GET'])
@token_required
def get_roles():
    start_time = time.time()
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
        
        end_time = time.time()
        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": roles,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTime": end_time - start_time
        }), 200

        return jsonify({
            "data" : paginate_query(cur,base_query),
            "status" : 200})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Get role by ID --------------------- #
@role_bp.route('/<int:role_id>', methods=['GET'])
@token_required
def get_role(role_id):
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        role = cur.fetchone()
        cur.close()
        end_time = time.time()

        if role:
            return jsonify({
                "data" : role,
                "status" :200,
                "execution_time": end_time - start_time
            }), 200
        else:
            return jsonify({"error": "Role not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Create a new role --------------------- #
@role_bp.route('/', methods=['POST'])
@token_required
def create_role():
    start_time = time.time()

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
        end_time = time.time()

        return jsonify({"message": "Role created successfully",
                        "status" : 201,
                        "execution_time": end_time - start_time}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Update an existing role --------------------- #
@role_bp.route('/<int:role_id>', methods=['PUT'])
@token_required
def update_role(role_id):
    start_time = time.time()

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
        end_time = time.time()

        return jsonify({"message": "Role updated successfully",
                        "status" : 200,
                        "execution_time": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------- Delete a role --------------------- #
@role_bp.route('/<int:role_id>', methods=['DELETE'])
@token_required
def delete_role(role_id):
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        mysql.connection.commit()
        cur.close()
        end_time = time.time()

        return jsonify({"message": "Role deleted successfully",
                        "status" : 200,
                        "execution_time": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#--------------------Search Role by name---------------------#
@role_bp.route('/search/<string:role_name>', methods=['GET'])
@token_required
def search_role(role_name):
    start_time = time.time()

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM roles WHERE role_name LIKE %s",
            ('%' + role_name + '%',)
        )
        results = cur.fetchall()
        cur.close()

        roles = []
        for result in results:
            roles.append({
                "id": result[0],
                "role_name": result[1],
                "status" : 200
            })

        if not roles:
            return jsonify({"message": "No roles found"}), 404
        end_time = time.time()
        roles.append({"execution_time": end_time - start_time})


        return jsonify(roles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#===========================================================#

# ---------------------- UPDATE ROLE PERMISSIONS (ADMIN ONLY) ---------------------- 
@role_bp.route('/update_permission/<int:id>', methods=['PUT'])
@token_required
def update_role_permissions(id):
    start_time = time.time()

    data = request.get_json()
    module_name = data.get('module')
    
    reception_val = data.get('reception') 
    admin_val = data.get('admin')
    tech_val = data.get('tech')

    # Data validation here (optional but recommended)

    cursor = current_app.mysql.connection.cursor() # DictCursor ki zaroorat nahi update mein
    try:
        update_query = """
            UPDATE role_management 
            SET module = %s, reception = %s, admin = %s, tech = %s 
            WHERE id = %s
        """
        
        # Tarteeb ka khayal rakhein: (module_name, reception_val, admin_val, tech_val, id)
        cursor.execute(update_query, (module_name, reception_val, admin_val, tech_val, id,))
        
        if cursor.rowcount == 0:
            return jsonify({"message": f"Role ID {id} not found."}), 404

        current_app.mysql.connection.commit()
        end_time = time.time()

        
    except Exception as e:
        current_app.mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

    return jsonify({"message": "update successfuly..", "id": id,"execution_time": end_time - start_time
})


# ---------------------- GET ALL PERMISSIONS (ADMIN ONLY) ---------------------- #
@role_bp.route('/role_get', methods=['GET'])
@token_required
def get_all_permissions():
    start_time = time.time()

    cursor = current_app.mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * FROM role_management")
    data = cursor.fetchall()
    cursor.close()
    end_time = time.time()
    data.append({"execution_time": end_time - start_time})
    return jsonify(data), 200

