from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL
import jwt
import datetime

authentication_bp = Blueprint('authentication', __name__, url_prefix='/api/auth')
mysql = MySQL()
#===================== Authentication Operations =====================

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

        #  Generate JWT Token with Expiry
        expiry_hours = current_app.config['TOKEN_EXPIRY_HOURS']
        payload = {
            "user_id": str(user["id"]),
            "user_name": user["user_name"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)
        }

        # token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        token = jwt.encode({"some": "payload"}, "secret", algorithm="HS256")

        return jsonify({
            "status": 20043,
            "message": "Login successful",
            "token": token,
            "user": user
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------- LOGOUT ---------------------- #
@authentication_bp.route('/logout', methods=['POST'])
def logout_user():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token missing"}), 400

        token = auth_header.split(" ")[1]
        #  Token ko blacklist mein add kar do
        current_app.blacklisted_tokens.add(token)

        return jsonify({"message": "Logout successful."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
