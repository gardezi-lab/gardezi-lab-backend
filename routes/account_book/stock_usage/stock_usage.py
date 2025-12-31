import time
import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
import math

# Blueprint
stock_usage_bp = Blueprint('stock_usage', __name__, url_prefix='/api/stock_usage')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_usage_bp.route('/', methods=['POST'])
@token_required
def create_stock_usage():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')

        if not stock_item_id or not qty:
            return jsonify({"error": "stock_item_id and qty are required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO stock_usage (stock_item_id, qty, date_created)
            VALUES (%s, %s, NOW())
        """, (stock_item_id, qty))
        mysql.connection.commit()
        usage_id = cursor.lastrowid
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({
            "message": "Stock usage created successfully",
            "usage_id": usage_id,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- READ ALL (GET) -------------------- #
@stock_usage_bp.route('/', methods=['GET'])
@token_required
def get_all_stock_usage():
    start_time = time.time()
    cursor = None
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # Soft delete aware
        where_clause = "WHERE su.trash = 0"
        values = []

        if search:
            where_clause += " AND si.name LIKE %s"
            values.append(f"%{search}%")

        # Count total records
        count_query = f"""
            SELECT COUNT(DISTINCT su.id) AS total
            FROM stock_usage su
            JOIN stock_items si ON su.stock_item_id = si.id
            {where_clause}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"] or 0

        # Fetch paginated data
        data_query = f"""
            SELECT 
                su.id,
                su.stock_item_id,
                si.name AS item_name,
                su.qty,
                su.date_created
            FROM stock_usage su
            JOIN stock_items si ON su.stock_item_id = si.id
            {where_clause}
            ORDER BY su.id DESC
            LIMIT %s OFFSET %s
        """
        data_values = values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        usage = cursor.fetchall()

        execution_time = time.time() - start_time
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1

        return jsonify({
            "data": usage,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": execution_time
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

    finally:
        if cursor:
            cursor.close()


# -------------------- READ ONE (GET by ID) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_stock_usage(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                su.id,
                su.stock_item_id,
                si.name AS item_name,
                su.qty,
                su.date_created
            FROM stock_usage su
            JOIN stock_items si ON su.stock_item_id = si.id
            WHERE su.id = %s
        """, (id,))
        usage = cursor.fetchone()
        cursor.close()

        execution_time = time.time() - start_time
        if not usage:
            return jsonify({"message": "Stock usage not found", "execution_time": execution_time}), 404

        return jsonify({"data": usage, "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- UPDATE (PUT) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_stock_usage(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()
        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')

        if not stock_item_id or not qty:
            return jsonify({"error": "stock_item_id and qty are required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_usage WHERE id = %s", (id,))
        usage = cursor.fetchone()

        if not usage:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock usage not found", "execution_time": execution_time}), 404

        cursor.execute("""
            UPDATE stock_usage
            SET stock_item_id = %s, qty = %s
            WHERE id = %s
        """, (stock_item_id, qty, id))
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({"message": "Stock usage updated successfully", "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- DELETE (SOFT DELETE) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_stock_usage(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if usage exists and not already deleted
        cursor.execute(
            "SELECT id FROM stock_usage WHERE id = %s AND trash = 0",
            (id,)
        )
        usage = cursor.fetchone()
        if not usage:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock usage not found", "execution_time": execution_time}), 404

        # Soft delete
        cursor.execute(
            "UPDATE stock_usage SET trash = 1 WHERE id = %s",
            (id,)
        )
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({
            "message": "Stock usage deleted successfully",
            "execution_time": execution_time
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

