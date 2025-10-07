
import math
from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL
import MySQLdb

results_bp = Blueprint('results', __name__, url_prefix='/api/results')
mysql = MySQL()

# -------------------- Create a new result -------------------- #
@results_bp.route('/', methods=['POST'])
def create_result():
    try:
        data = request.get_json()
        name = data.get("name")
        mr = data.get("mr")
        date = data.get("date")
        add_results = data.get("add_results")
        sample = data.get("sample")

        if not name:
            return jsonify({"error": "Name is required"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO results (name, mr, date, add_results, sample) VALUES (%s, %s, %s, %s, %s)",
            (name, mr, date, add_results, sample)
        )
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            "message": "Result added successfully",
            "id": new_id,
            "name": name,
            "mr": mr,
            "date": date,
            "add_results": add_results,
            "sample": sample
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Get all results (with search + pagination) -------------------- #
@results_bp.route('/', methods=['GET'])
def get_results():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM results"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("(name LIKE %s OR mr LIKE %s OR sample LIKE %s OR add_results LIKE %s)")
            values.extend([f"%{search}%"] * 4)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        results = cursor.fetchall()
        cursor.close()

        formatted_results = [
            {
                "id": r["id"],
                "name": r["name"],
                "mr": r["mr"],
                "date": r["date"].strftime("%Y-%m-%d") if r["date"] else None,
                "add_results": r["add_results"],
                "sample": r["sample"]
            }
            for r in results
        ]

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": formatted_results,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Get result by ID -------------------- #
@results_bp.route('/<int:result_id>', methods=['GET'])
def get_result_by_id(result_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return jsonify({"error": "Result not found"}), 404

        if row["date"]:
            row["date"] = row["date"].strftime("%Y-%m-%d")

        return jsonify(row), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Update result -------------------- #
@results_bp.route('/<int:result_id>', methods=['PUT'])
def update_result(result_id):
    try:
        data = request.get_json()
        name = data.get("name")
        mr = data.get("mr")
        date = data.get("date")
        add_results = data.get("add_results")
        sample = data.get("sample")

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"error": "Result not found"}), 404

        update_query = """
            UPDATE results
            SET name=%s, mr=%s, date=%s, add_results=%s, sample=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (name, mr, date, add_results, sample, result_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Result updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Delete result -------------------- #
@results_bp.route('/<int:result_id>', methods=['DELETE'])
def delete_result(result_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"error": "Result not found"}), 404

        cursor.execute("DELETE FROM results WHERE id = %s", (result_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Result deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# -------------------- Get only pending results (no add_results) -------------------- #
@results_bp.route('/pending', methods=['GET'])
def get_pending_results():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Optional search & pagination
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        base_query = "SELECT * FROM results WHERE (add_results IS NULL OR add_results = '')"
        values = []

        if search:
            base_query += " AND (name LIKE %s OR mr LIKE %s OR sample LIKE %s)"
            values.extend([f"%{search}%"] * 3)

        # Count total pending
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        pending_results = cursor.fetchall()
        cursor.close()

        formatted = [
            {
                "id": r["id"],
                "name": r["name"],
                "mr": r["mr"],
                "date": r["date"].strftime("%Y-%m-%d") if r["date"] else None,
                "add_results": r["add_results"],
                "sample": r["sample"]
            }
            for r in pending_results
        ]

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": formatted,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
