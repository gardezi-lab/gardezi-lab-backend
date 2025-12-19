import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL

# Blueprint
stock_usage_report_bp = Blueprint(
    'stock_usage_report', __name__, url_prefix='/api/stock_usage_report'
)
mysql = MySQL()

# -------------------- CREATE -------------------- #
@stock_usage_report_bp.route('/', methods=['POST'])
@token_required
def create_stock_usage():
    try:
        mysql = current_app.mysql
        data = request.get_json()
        quantity = data.get('quantity')
        rate = data.get('rate')
        date = data.get('date')

        if not all([quantity, rate, date]):
            return jsonify({"error": "Missing fields"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "INSERT INTO `stock_usage_reporting` (quantity, rate, date) VALUES (%s, %s, %s)",
            (quantity, rate, date)
        )
        mysql.connection.commit()
        usage_id = cursor.lastrowid
        cursor.close()

        return jsonify({"message": "Created", "id": usage_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# -------------------- READ ALL -------------------- #
@stock_usage_report_bp.route('/', methods=['GET'])
@token_required
def get_all_stock_usage():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # -------- Query Params -------- #
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # -------- Base Query -------- #
        where_clause = "WHERE 1=1"
        values = []

        if search:
            where_clause += " AND (date LIKE %s)"
            values.append(f"%{search}%")

        # -------- Data Query (Pagination) -------- #
        query = f"""
            SELECT *
            FROM stock_usage_reporting
            {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        values.extend([record_per_page, offset])

        cursor.execute(query, values)
        usages = cursor.fetchall()
        cursor.close()

        # -------- SAME RESPONSE FORMAT -------- #
        result = []
        for u in usages:
            total = float(u['quantity']) * float(u['rate'])
            result.append({
                "id": u['id'],
                "quantity": u['quantity'],
                "rate": u['rate'],
                "date": str(u['date']),
                "total": total
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ONE -------------------- #
@stock_usage_report_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_stock_usage(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM `stock_usage_reporting` WHERE id = %s", (id,))
        u = cursor.fetchone()
        cursor.close()

        if not u:
            return jsonify({"message": "Not found"}), 404

        total = float(u['quantity']) * float(u['rate'])
        result = {
            "id": u['id'],
            "quantity": u['quantity'],
            "rate": u['rate'],
            "date": str(u['date']),
            "total": total
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- UPDATE -------------------- #
@stock_usage_report_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_stock_usage(id):
    try:
        mysql = current_app.mysql
        data = request.get_json()
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM `stock_usage_reporting` WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"message": "Not found"}), 404

        cursor.execute(
            "UPDATE `stock_usage_reporting` SET quantity=%s, rate=%s, date=%s WHERE id=%s",
            (data.get('quantity'), data.get('rate'), data.get('date'), id)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- DELETE -------------------- #
@stock_usage_report_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_stock_usage(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM `stock_usage_reporting` WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"message": "Not found"}), 404

        cursor.execute("DELETE FROM `stock_usage_reporting` WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET STOCK USAGE WITH DATE FILTER -------------------- #
@stock_usage_report_bp.route('/', methods=['GET'])
@token_required
def get_stock_usage_by_date():
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Base query
        base_query = """
            SELECT 
                id,
                quantity,
                rate,
                date,
                (quantity * rate) AS total
            FROM stock_usage_reporting
            WHERE 1=1
        """

        params = []

        # Add date filter only if both dates are provided
        if from_date and to_date:
            base_query += " AND DATE(date) BETWEEN %s AND %s"
            params.extend([from_date, to_date])

        base_query += " ORDER BY id DESC"

        cursor.execute(base_query, params)
        usages = cursor.fetchall()
        cursor.close()

        return jsonify({
            "data": usages,
            "count": len(usages)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
