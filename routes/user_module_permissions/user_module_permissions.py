from flask import Blueprint, jsonify, current_app,request
from MySQLdb.cursors import DictCursor

permission_bp = Blueprint('permission', __name__, url_prefix='/api/permission')

@permission_bp.route('/', methods=['GET'])
def get_all_permissions():
    try:
        # Database connection
        conn = current_app.mysql.connection
        cursor = conn.cursor(DictCursor)

        # Query
        cursor.execute("SELECT * FROM user_module_permissions")
        data = cursor.fetchall()
        cursor.close()

        # Simple formatted output
        result = []
        for row in data:
            result.append({
                "moduleid": row["id"],
                "modulename": row["modulename"],
                "crud": {
                    "reception": row["reception"],
                    "technician": row["technician"],
                    "pathologist": row["pathologist"],
                    "manager": row["manager"],
                    "doctor": row["doctor"],
                    "patient": row["patient"],
                    "accountant": row["accountant"]
                }
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------------- UPDATE PERMISSIONS BY USERID ---------------- #
@permission_bp.route('/<int:userid>', methods=['PUT'])
def update_permissions(userid):
    try:
        conn = current_app.mysql.connection
        cursor = conn.cursor()

        data = request.get_json()
        modules = data.get("modules", [])

        if not modules:
            return jsonify({"error": "Modules list is required"}), 400

        # Loop through each module and update its CRUD values
        for module in modules:
            modulename = module.get("modulename")
            crud = module.get("crud", {})

            reception = crud.get("reception", 0)
            technician = crud.get("technician", 0)
            pathologist = crud.get("pathologist", 0)
            manager = crud.get("manager", 0)
            doctor = crud.get("doctor", 0)
            patient = crud.get("patient", 0)
            accountant = crud.get("accountant", 0)

            # Update query based on modulename and userid
            cursor.execute("""
                UPDATE user_module_permissions 
                SET reception=%s, technician=%s, pathologist=%s, manager=%s, 
                    doctor=%s, patient=%s, accountant=%s
                WHERE modulename=%s
            """, (reception, technician, pathologist, manager, doctor, patient, accountant, modulename))

        conn.commit()
        cursor.close()

        return jsonify({"message": f"Permissions updated successfully for userid {userid}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500