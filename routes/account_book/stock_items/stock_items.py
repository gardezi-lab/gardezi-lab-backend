import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
import time
import math

stock_items_bp = Blueprint('stock_items', __name__, url_prefix='/api/stock_items')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_items_bp.route('/', methods=['POST'])
@token_required
def create_stock_item():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        name = data.get('name')
        if not name:
            return jsonify({"error": "Name is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("INSERT INTO stock_items (name) VALUES (%s)", (name,))
        mysql.connection.commit()
        item_id = cursor.lastrowid
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({
            "message": "Stock item created successfully",
            "item_id": item_id,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- READ ALL (GET) -------------------- #
@stock_items_bp.route('/', methods=['GET'])
@token_required
def get_all_stock_items():
    start_time = time.time()
    cursor = None
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        where_clause = "WHERE 1=1"
        values = []

        if search:
            where_clause += " AND name LIKE %s"
            values.append(f"%{search}%")

        # Count total records
        count_query = f"SELECT COUNT(*) AS total FROM stock_items {where_clause}"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"] or 0

        # Fetch paginated data
        data_query = f"""
            SELECT id, name
            FROM stock_items
            {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        data_values = values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        items = cursor.fetchall()

        execution_time = time.time() - start_time
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1

        return jsonify({
            "data": items,
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
@stock_items_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_stock_item(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, name FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()
        cursor.close()

        execution_time = time.time() - start_time
        if not item:
            return jsonify({"message": "Stock item not found", "execution_time": execution_time}), 404

        return jsonify({"data": item, "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- UPDATE (PUT) -------------------- #
@stock_items_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_stock_item(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({"error": "Name is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()
        if not item:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock item not found", "execution_time": execution_time}), 404

        cursor.execute("UPDATE stock_items SET name = %s WHERE id = %s", (name, id))
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({"message": "Stock item updated successfully", "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- DELETE (DELETE) -------------------- #
@stock_items_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_stock_item(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()
        if not item:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock item not found", "execution_time": execution_time}), 404

        cursor.execute("DELETE FROM stock_items WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({"message": "Stock item deleted successfully", "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500
