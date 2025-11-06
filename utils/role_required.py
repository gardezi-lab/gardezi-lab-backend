import jwt
from functools import wraps
from flask import request, jsonify, current_app
from MySQLdb.cursors import DictCursor

# ... (imports: functools, request, jsonify, current_app, DictCursor) ...

def role_required_jwt(module_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Pehle token ko verify karein (using your existing token_required logic or a part of it)
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token missing"}), 401
            token = auth_header.split(" ")[1]

            try:
                # Token decode karein (blacklisting check is not included here, but should be)
                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                user_role = data.get("user_role", None) # Payload se role extract karein
                
                if not user_role:
                     return jsonify({"message": "Role not found in token payload"}), 403

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401
            
            user_role = user_role.lower()
            user_role = user_role.strip()
            
            # ***** Role Permission Check Logic *****
            user_role = user_role.lower()
            conn = current_app.mysql.connection
            cursor = conn.cursor(DictCursor)

            try:
                cursor.execute("SELECT * FROM role_management WHERE module=%s", (module_name,))
                module_permissions = cursor.fetchone()

                if not module_permissions:
                    return jsonify({"message": f"Module '{module_name}' not found"}), 404

                # Check DB permission (jaise aapne pehle bataya tha)
                if str(module_permissions.get(user_role)) != "1":
                    return jsonify({"message": f"Access Denied for role '{user_role}'"}), 403
            finally:
                cursor.close()

            # Agar sab theek hai, to original function run karein
            return func(*args, **kwargs)
        return wrapper
    return decorator
