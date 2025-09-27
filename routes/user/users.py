import random, string
from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

users_bp = Blueprint('users', __name__, url_prefix='/api/users')
mysql = MySQL()

#===================== Users CRUD Operations =====================

#--------------------- User POST -------------------
@users_bp.route('/', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        plain_password = data.get("password")
        if not plain_password:
            plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        age = data.get("age")
        role = data.get("role")

        # Validation
        if not all([name, contact_no, user_name, age, role]):
            return jsonify({"error": "All fields except password are required"}), 400

        if isinstance(name, int) or isinstance(user_name, int):
            return jsonify({"message": "Name or username cannot be number"}), 400

        if isinstance(age, str):
            return jsonify({"message": "Age cannot be string"}), 400

        insert_query = """
            INSERT INTO users (name, contact_no, user_name, password, role, age)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor = mysql.connection.cursor()
        cursor.execute(insert_query, (
            name,
            contact_no,
            user_name,
            plain_password,
            role,
            age
        ))
        mysql.connection.commit()

        return jsonify({
            "message": "User created successfully",
            "name": name,
            "contact_no": contact_no,
            "user_name": user_name,
            "role": role,
            "age": age,
            "password": plain_password
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- Users GET --------------------
@users_bp.route('/', methods=['GET'])
def get_users():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, contact_no, user_name, password, age, role
            FROM users
        """)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        users = [dict(zip(column_names, row)) for row in rows]
        return jsonify(users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#---------------------- User Get by ID -------------------
@users_bp.route('/<int:id>', methods=['GET'])
def get_user_by_id(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, contact_no, user_name, password, role, age 
            FROM users WHERE id = %s
        """, (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        column_names = [desc[0] for desc in cursor.description]
        return jsonify(dict(zip(column_names, row))), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- User Update --------------------
@users_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        plain_password = data.get("password")
        role = data.get("role")
        age = data.get("age")

        # Check user exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404

        update_query = """
            UPDATE users
            SET name=%s, contact_no=%s, user_name=%s, password=%s, role=%s, age=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (
            name, contact_no, user_name, plain_password, role, age, id
        ))
        mysql.connection.commit()

        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- User Delete --------------------
@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404

        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- Users Search by Name --------------------
@users_bp.route('/search/<string:name>', methods=['GET'])
def search_users(name):
    try:
        cursor = mysql.connection.cursor()
        search_query = """
            SELECT id, name, contact_no, user_name, password, age, role
            FROM users
            WHERE name LIKE %s
        """
        cursor.execute(search_query, (f"%{name}%",))
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": "User not found"}), 404

        column_names = [desc[0] for desc in cursor.description]
        users = [dict(zip(column_names, row)) for row in rows]
        return jsonify(users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#----------------- Get Role Wise User List ---------------------
@users_bp.route('/datalist/<string:role_name>', methods=['GET'])
def datalist_role(role_name):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT role FROM users WHERE role LIKE %s",
            ('%' + role_name + '%',)
        )
        results = cur.fetchall()
        cur.close()

        roles = [{"role_name": r[0]} for r in results]

        if not roles:
            return jsonify({"message": "No roles found"}), 404

        return jsonify(roles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
