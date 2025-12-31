from flask import Blueprint, request, jsonify, current_app, g
from MySQLdb.cursors import DictCursor
import jwt
import datetime
import time
from functools import wraps
import re

authentication_bp = Blueprint(
    'authentication_bp',
    __name__,
    url_prefix='/api/auth'
)

# ------------------ TOKEN DECORATOR ------------------ #
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token missing"}), 401

        token = auth_header.split(" ")[1]
        try:
            if token in current_app.blacklisted_tokens:
                return jsonify({"error": "Token has been revoked"}), 401

            data = jwt.decode(
                token,
                str(current_app.config['SECRET_KEY']),
                algorithms=["HS256"]
            )
            g.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# ------------------ DYNAMIC PERMISSIONS FETCH ------------------ #
def get_role_permissions(role):
    """
    Check if the role column exists and return permissions in { 'module': value } format.
    """
    mysql = current_app.mysql
    cursor = mysql.connection.cursor(DictCursor)

    try:
        # 1. Pehle confirm karein ke column exist karta hai (Small/Large case handle karne ke liye)
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'user_module_permissions' 
            AND LOWER(COLUMN_NAME) = LOWER(%s)
        """, (role,))
        
        column_info = cursor.fetchone()

        if not column_info:
            print(f"DEBUG: Role column '{role}' not found in DB.")
            cursor.close()
            return {}

        # Sahi column name jo DB mein hai (e.g. 'Ali' ya 'ali')
        db_column_name = column_info['COLUMN_NAME']
        print("DEBUG: Found role column in DB:", db_column_name)

        # 2. Query: Modulename aur us role ki permission uthao
        # Backticks (`) lagana zaroori hai kyunki role names dynamic hain
        query = f"SELECT modulename, `{db_column_name}` AS allowed FROM user_module_permissions"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        # 3. Response format: {"Dashboard": 1, "Reports": 0}
        permissions_dict = {}
        for row in rows:
            if row["modulename"]: # Ensure module name is not null
                permissions_dict[row["modulename"]] = row["allowed"]
        
        return permissions_dict

    except Exception as e:
        print(f"Database Error: {str(e)}")
        return {}

# ---------------------- LOGIN (DYNAMIC) ---------------------- #
@authentication_bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 1. User find karein
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # 2. Password check (Plain text - security ke liye hash use karein baad mein)
        if user["password"] != password:
            return jsonify({"error": "Invalid credentials"}), 401

        role = user["role"]

        # 3. Dynamic Permissions (Ab koi ALLOWED_ROLES list ki zaroorat nahi)
        permissions = get_role_permissions(role)

        # 4. JWT Token Generation
        payload = {
            "user_id": user["id"],
            "email": user["email"],
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }

        token = jwt.encode(payload, str(current_app.config["SECRET_KEY"]), algorithm="HS256")
        
        return jsonify({
            "status": 200,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "name": user.get("name") # Agar name field hai toh
            },
            "permissions": permissions
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------- LOGOUT ---------------------- #
@authentication_bp.route('/logout', methods=['POST'])
@token_required
def logout_user():
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(" ")[1]
        current_app.blacklisted_tokens.add(token)

        return jsonify({
            "status": 200,
            "message": "Logout successful"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
