from flask import Blueprint, jsonify, current_app,request
from MySQLdb.cursors import DictCursor
import time
from routes.authentication.authentication import token_required

permission_bp = Blueprint('permission', __name__, url_prefix='/api/permission')

@permission_bp.route('/', methods=['GET'])
@token_required
def get_all_permissions():
    start_time = time.time()
    try:
        # Pagination (same style as you asked)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 30, type=int)
        offset = (current_page - 1) * record_per_page

        # DB connection
        conn = current_app.mysql.connection
        cursor = conn.cursor(DictCursor)

        # Total records
        cursor.execute("SELECT COUNT(*) AS total FROM user_module_permissions")
        total_records = cursor.fetchone()["total"]

        # Paginated data
        cursor.execute("""
            SELECT * FROM user_module_permissions
            LIMIT %s OFFSET %s
        """, (record_per_page, offset))
        data = cursor.fetchall()
        cursor.close()

        # Format response
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

        end_time = time.time()

        return jsonify({
            "modules": result,
            "pagination": {
                "current_page": current_page,
                "record_per_page": record_per_page,
                "total_records": total_records,
                "total_pages": (total_records + record_per_page - 1) // record_per_page
            },
            "status": 200,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- UPDATE PERMISSIONS BY USERID ---------------- #
@permission_bp.route('/', methods=['PUT'])
@token_required
def update_permissions():
    start_time = time.time()
    try:
        conn = current_app.mysql.connection
        cursor = conn.cursor()

        data = request.get_json()
        modules = data.get("modules", [])

        if not modules:
            return jsonify({"error": "Modules list is required"}), 400

        # Loop through each module and update its CRUD values
        for module in modules:
            moduleid = module.get("moduleid")  
            crud = module.get("crud", {})

            reception = crud.get("reception", 0)
            technician = crud.get("technician", 0)
            pathologist = crud.get("pathologist", 0)
            manager = crud.get("manager", 0)
            doctor = crud.get("doctor", 0)
            patient = crud.get("patient", 0)
            accountant = crud.get("accountant", 0)

            cursor.execute("""
                UPDATE user_module_permissions 
                SET reception=%s, technician=%s, pathologist=%s, manager=%s, 
                    doctor=%s, patient=%s, accountant=%s
                WHERE id=%s   
            """, (reception, technician, pathologist, manager, doctor, patient, accountant, moduleid))


        conn.commit()
        cursor.close()
        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({"message": "Permissions updated successfully..............",
                        "status": 200,
                        "execution_time": execution_time}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500