import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
import MySQLdb
import time
from routes.authentication.authentication import token_required



# Blueprint with API prefix
interpretation_bp = Blueprint("interpretations", __name__, url_prefix="/api/interpretations")

# -------- Helper: Validation --------
def validate_interpretation_data(data, is_update=False):
    errors = []
    if not is_update:
        if not data.get("code"):
            errors.append("code is required")
        if not data.get("heading"):
            errors.append("heading is required")
    return errors if errors else None


# -------------------- CREATE -------------------- #
@interpretation_bp.route("/", methods=["POST"])
@token_required
def create_interpretation():
    start_time = time.time()
    try:

        mysql = current_app.mysql
        data = request.get_json()
        errors = validate_interpretation_data(data, is_update=False)
        if errors:
            return jsonify({"error": errors}), 400

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO interpretations (code, heading, detail) VALUES (%s, %s, %s)",
            (data["code"], data["heading"], data.get("detail")),
        )
        mysql.connection.commit()
        cur.close()
        end_time = time.time()

        return jsonify({"message": "Interpretation created successfully",
                        "execution_time": end_time - start_time}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# -------------------- GET with Search + Pagination -------------------- #
@interpretation_bp.route("/", methods=["GET"])
@token_required
def get_interpretations():
    start_time = time.time()
    try:
        mysql = current_app.mysql # type: ignore
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
       
        # Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM interpretations"
        where_clauses = []
        values = []

        # Search condition
        if search:
            where_clauses.append("(code LIKE %s OR heading LIKE %s OR detail LIKE %s)")
            values.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        interpretations = cursor.fetchall()
        
        end_time = time.time()
        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": interpretations,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTime": end_time - start_time
        }), 200

    except Exception as e:   
        return jsonify({"error": str(e)}), 500


# -------------------- GET by ID -------------------- #
@interpretation_bp.route("/<int:id>", methods=["GET"])
@token_required
def get_interpretation_by_id(id):
    strat_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT * FROM interpretations WHERE id=%s", (id,))
        interpretation = cursor.fetchone()
        cursor.close()

        if not interpretation:
            return jsonify({"error": "Interpretation not found"}), 404
        end_time = time.time()

        interpretation['execution_time'] = end_time - strat_time
        return jsonify(interpretation), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- UPDATE -------------------- #
@interpretation_bp.route("/<int:id>", methods=["PUT"])
@token_required
def update_interpretation(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE interpretations SET code=%s, heading=%s, detail=%s WHERE id=%s",
            (data.get("code"), data.get("heading"), data.get("detail"), id),
        )
        mysql.connection.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Interpretation not found"}), 404

        cur.close()
        end_time = time.time()
        
        return jsonify({"message": "Interpretation updated","status": 200,
                        "execution_time": end_time - start_time})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


# -------------------- DELETE -------------------- #
@interpretation_bp.route("/<int:id>", methods=["DELETE"])
@token_required
def delete_interpretation(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM interpretations WHERE id=%s", (id,))
        mysql.connection.commit()
        deleted_rows = cur.rowcount
        cur.close()

        if deleted_rows == 0:
            return jsonify({"error": "Interpretation not found"}), 404
        end_time = time.time()

        return jsonify({"message": "Interpretation deleted successfully","status":200,"execution_time": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
