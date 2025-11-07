from functools import wraps
from flask import request, jsonify, current_app
from MySQLdb.cursors import DictCursor

def role_required(module_name, action):
    """
    Check user permissions (view, add, edit, delete) from user_module_permissions table.
    Requires `userid` in request header.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            userid = request.headers.get("userid")
            if not userid:
                return jsonify({"error": "userid header is required"}), 400

            conn = current_app.mysql.connection
            cursor = conn.cursor(DictCursor)
            cursor.execute("""
                SELECT view, add_permission, edit_permission, delete_permission
                FROM user_module_permissions
                WHERE userid = %s AND modulename = %s
            """, (userid, module_name))
            perm = cursor.fetchone()
            cursor.close()

            if not perm:
                return jsonify({"error": f"No permissions found for module '{module_name}'"}), 403

            # Action check
            allowed = {
                "view": perm["view"],
                "add": perm["add_permission"],
                "edit": perm["edit_permission"],
                "delete": perm["delete_permission"]
            }.get(action, 0)

            if not allowed:
                return jsonify({"error": f"Access Denied for {action.upper()} in {module_name}"}), 403

            return func(*args, **kwargs)
        return wrapper
    return decorator
