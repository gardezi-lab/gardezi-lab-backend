from flask import Blueprint, jsonify, current_app,request
from MySQLdb.cursors import DictCursor

permission_bp = Blueprint('permission', __name__, url_prefix='/api/permission')


@permission_bp.route('/', methods=['GET'])
def get_all_permissions():
    try:
        conn = current_app.mysql.connection
        cursor = conn.cursor(DictCursor)

        cursor.execute("""
            SELECT 
                id,
                userid, 
                modulename, 
                view, 
                `add_permission` AS `add`, 
                `edit_permission` AS `edit`, 
                `delete_permission` AS `delete`
            FROM user_module_permissions
        """)
        records = cursor.fetchall()
        cursor.close()

        # Grouping by userid
        result = {}
        for row in records:
            uid = row['userid']
            if uid not in result:
                result[uid] = []
            result[uid].append({
                "modulename": row['modulename'],
                "moduleid": row['id'],
                "crud": {
                    "view": row['view'],
                    "add": row['add'],
                    "edit": row['edit'],
                    "delete": row['delete']
                }
            })

        # Final response format (list of all users)
        response = []
        for uid, modules in result.items():
            response.append({
                "userid": uid,
                "modules": modules
            })

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@permission_bp.route('/', methods=['POST'])
def create_permissions():
    try:
        data = request.get_json()
        userid = data.get('userid')
        modules = data.get('modules', [])

        if not userid or not modules:
            return jsonify({"error": "userid and modules are required"}), 400

        conn = current_app.mysql.connection
        cursor = conn.cursor()

        # Delete old permissions before inserting new ones
        cursor.execute("DELETE FROM user_module_permissions WHERE userid = %s", (userid,))

        # Insert all modules
        for module in modules:
            modulename = module['modulename']
            crud = module['crud']
            cursor.execute("""
                INSERT INTO user_module_permissions 
                (userid, modulename, view, add_permission, edit_permission, delete_permission)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                userid,
                modulename,
                crud.get('view', 0),
                crud.get('add', 0),
                crud.get('edit', 0),
                crud.get('delete', 0)
            ))

        conn.commit()
        cursor.close()

        return jsonify({"message": "Permissions added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@permission_bp.route('/<int:userid>', methods=['PUT'])
def update_permissions(userid):
    try:
        data = request.get_json()
        modules = data.get('modules', [])

        if not modules:
            return jsonify({"error": "modules are required"}), 400

        conn = current_app.mysql.connection
        cursor = conn.cursor()

        # Purane modules delete kar do (same userid ke)
        cursor.execute("DELETE FROM user_module_permissions WHERE userid = %s", (userid,))

        # Naye modules insert karo
        for module in modules:
            modulename = module['modulename']
            crud = module['crud']
            cursor.execute("""
                INSERT INTO user_module_permissions 
                (userid, modulename, view, add_permission, edit_permission, delete_permission)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                userid,
                modulename,
                crud.get('view', 0),
                crud.get('add', 0),
                crud.get('edit', 0),
                crud.get('delete', 0)
            ))

        conn.commit()
        cursor.close()

        return jsonify({"message": f"Permissions updated successfully for userid {userid}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@permission_bp.route('/', methods=['DELETE'])
def delete_permissions():
    try:
        userid = request.args.get('userid')
        modulename = request.args.get('modulename')

        if not userid:
            return jsonify({"error": "userid is required"}), 400

        conn = current_app.mysql.connection
        cursor = conn.cursor()

        if modulename:
            cursor.execute("DELETE FROM user_module_permissions WHERE userid = %s AND modulename = %s", (userid, modulename))
        else:
            cursor.execute("DELETE FROM user_module_permissions WHERE userid = %s", (userid,))

        conn.commit()
        cursor.close()

        return jsonify({"message": "Permission(s) deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@permission_bp.route('/by_user', methods=['GET'])
def get_permissions_by_userid():
    try:
        userid = request.args.get('userid')

        if not userid:
            return jsonify({"error": "userid is required"}), 400

        conn = current_app.mysql.connection
        cursor = conn.cursor(DictCursor)

        cursor.execute("""
            SELECT 
                id,
                modulename,
                view,
                `add_permission` AS `add`,
                `edit_permission` AS `edit`,
                `delete_permission` AS `delete`
            FROM user_module_permissions
            WHERE userid = %s
        """, (userid,))

        records = cursor.fetchall()
        cursor.close()

        result = {
            # "userid": int(userid),
    
            "modules": []
        }

        for row in records:
            result["modules"].append({
                "modulename": row["modulename"],
                "module_id": row['id'],
                "crud": {
                    "view": row["view"],
                    "add": row["add"],
                    "edit": row["edit"],
                    "delete": row["delete"]
                }
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
