from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL
import jwt
import datetime
from functools import wraps

authentication_bp = Blueprint('authentication_bp', __name__, url_prefix='/api/auth')
mysql = MySQL()

# ------------------ Helper Decorator ------------------ #
def token_required(f):
    """Decorator to protect routes that need authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token missing"}), 401

        token = auth_header.split(" ")[1]

        try:
            # Check if token is blacklisted
            if token in current_app.blacklisted_tokens:
                return jsonify({"error": "Token has been revoked"}), 401

            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            request.user = data  # attach user info to request
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# ---------------------- LOGIN ---------------------- #
@authentication_bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        user_name = data.get("user_name")
        password = data.get("password")

        if not user_name or not password:
            return jsonify({"error": "Username and password are required"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_name = %s AND password = %s", (user_name, password))
        row = cursor.fetchone()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()

        if not row:
            return jsonify({"error": "Invalid credentials"}), 401

        user = dict(zip(column_names, row))

        # Generate JWT Token with Expiry
        expiry_hours = current_app.config.get('TOKEN_EXPIRY_HOURS', 12)
        payload = {
            "user_id": str(user["id"]),
            "user_name": user["user_name"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)
        }

        token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            "status": 200,
            "message": "Login successful",
            "token": token,
            "user": user
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------- LOGOUT ---------------------- #
@authentication_bp.route('/logout', methods=['POST'])
@token_required
def logout_user():
    try:
        # Token already verified by decorator
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(" ")[1]

        # Add token to blacklist
        current_app.blacklisted_tokens.add(token)

        return jsonify({
            "message": "Logout successful",
            "status": 200
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
