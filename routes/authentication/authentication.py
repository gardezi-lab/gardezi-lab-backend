from flask import Blueprint, request, jsonify, current_app, g
from MySQLdb.cursors import DictCursor
import jwt
import datetime
from functools import wraps

authentication_bp = Blueprint(
    'authentication_bp',
    __name__,
    url_prefix='/api/auth'
)

# ------------------ ROLE WHITELIST ------------------ #
ALLOWED_ROLES = ["Reception", "Doctor", "Technician", "Admin"]

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
                current_app.config['SECRET_KEY'],
                algorithms=["HS256"]
            )

            g.user = data

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# ------------------ GET ROLE PERMISSIONS ------------------ #
def get_role_permissions(role):
    if role not in ALLOWED_ROLES:
        return []

    mysql = current_app.mysql
    cursor = mysql.connection.cursor(DictCursor)

    query = f"""
        SELECT modulename, `{role}` AS allowed
        FROM user_module_permissions
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    return rows


# ---------------------- LOGIN ---------------------- #
@authentication_bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # USER FETCH
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # ❗ SIMPLE PASSWORD CHECK (NO HASH)
        if user["password"] != password:
            return jsonify({"error": "Invalid credentials"}), 401

        role = user["role"]

        # ROLE PERMISSIONS
        permissions_rows = get_role_permissions(role)

        permissions = {
            row["modulename"]: row["allowed"]
            for row in permissions_rows
        }

        # JWT
        payload = {
            "user_id": user["id"],
            "email": user["email"],
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }

        token = jwt.encode(payload, str(current_app.config["SECRET_KEY"]), algorithm="HS256")
        print(token)
        
        return jsonify({
            "status": 200,
            "message": "Login successful",
            "token": token,
            "user": user,
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
