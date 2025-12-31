import time
import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
from datetime import datetime
import math

# Blueprint
stock_purchase_bp = Blueprint('stock_purchase', __name__, url_prefix='/api/stock_purchases')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_purchase_bp.route('/', methods=['POST'])
@token_required
def create_stock_purchase():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        
        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')
        price = data.get('price')

        if not all([stock_item_id, qty, price]):
            return jsonify({"error": "All fields are required"}), 400

        qty = float(qty)
        price = float(price)
        totalamount = qty * price

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get default stock account
        cursor.execute("SELECT default_stock_account FROM account_setting WHERE id = 1")
        record = cursor.fetchone()
        default_cash_id = record['default_stock_account']

        date = datetime.now().strftime('%Y-%m-%d')

        # Insert journal voucher
        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, 'Stock Purchased', 'JV', ''))
        voucher_id = cursor.lastrowid

        # Insert journal voucher entries
        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_id, default_cash_id, totalamount, 0, 'JV', date))

        # cursor.execute("""
        #     INSERT INTO journal_voucher_entries
        #     (journal_voucher_id, account_head_id, dr, cr, type, date)
        #     VALUES (%s, %s, %s, %s, %s)
        # """, (voucher_id, 0, totalamount, 'JV', date))

        # Insert stock purchase
        cursor.execute("""
            INSERT INTO stock_purchases ( stock_item_id, qty, price, date_created)
            VALUES ( %s, %s, %s, NOW())
        """, ( stock_item_id, qty, price))
        mysql.connection.commit()
        purchase_id = cursor.lastrowid

        cursor.close()
        execution_time = time.time() - start_time

        return jsonify({
            "message": "Stock purchase created successfully",
            "purchase_id": purchase_id,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- READ ALL (GET) -------------------- #
@stock_purchase_bp.route('/', methods=['GET'])
@token_required
def get_all_stock_purchases():
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
        where_clause = "WHERE sp.trash = 0"
        values = []

        if search:
            where_clause += " AND (ah.name_head LIKE %s OR si.name LIKE %s)"
            values.extend([f"%{search}%", f"%{search}%"])

        # Count total records
        count_query = f"""
            SELECT COUNT(DISTINCT sp.id) AS total
            FROM stock_purchases sp
            LEFT JOIN account_heads ah ON sp.vendor_id = ah.id
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            {where_clause}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"] or 0

        # Fetch paginated data
        data_query = f"""
            SELECT 
                sp.id,
                sp.vendor_id,
                sp.stock_item_id,
                ah.name_head AS vendor_name,
                si.name AS item_name,
                sp.qty,
                sp.price,
                sp.date_created
            FROM stock_purchases sp
            LEFT JOIN account_heads ah ON sp.vendor_id = ah.id
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            {where_clause}
            ORDER BY sp.id DESC
            LIMIT %s OFFSET %s
        """
        data_values = values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        purchases = cursor.fetchall()

        execution_time = time.time() - start_time
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1

        return jsonify({
            "data": purchases,
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
@stock_purchase_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_stock_purchase(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                sp.id,
                sp.vendor_id,
                sp.stock_item_id,
                ah.name_head AS vendor_name,
                si.name AS item_name,
                sp.qty,
                sp.price,
                sp.date_created
            FROM stock_purchases sp
            LEFT JOIN account_heads ah ON sp.vendor_id = ah.id
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            WHERE sp.id = %s
        """, (id,))
        purchase = cursor.fetchone()
        cursor.close()

        execution_time = time.time() - start_time
        if not purchase:
            return jsonify({"message": "Stock purchase not found", "execution_time": execution_time}), 404

        return jsonify({"data": purchase, "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- UPDATE (PUT) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_stock_purchase(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        vendor_id = data.get('vendor_id')
        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')
        price = data.get('price')

        if not all([vendor_id, stock_item_id, qty, price]):
            return jsonify({"error": "All fields are required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_purchases WHERE id = %s", (id,))
        purchase = cursor.fetchone()

        if not purchase:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock purchase not found", "execution_time": execution_time}), 404

        cursor.execute("""
            UPDATE stock_purchases
            SET vendor_id = %s, stock_item_id = %s, qty = %s, price = %s
            WHERE id = %s
        """, (vendor_id, stock_item_id, qty, price, id))
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({"message": "Stock purchase updated successfully", "execution_time": execution_time}), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- DELETE (SOFT DELETE) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_stock_purchase(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if purchase exists and not already deleted
        cursor.execute(
            "SELECT id FROM stock_purchases WHERE id = %s AND trash = 0",
            (id,)
        )
        purchase = cursor.fetchone()
        if not purchase:
            cursor.close()
            execution_time = time.time() - start_time
            return jsonify({"message": "Stock purchase not found", "execution_time": execution_time}), 404

        # Soft delete
        cursor.execute(
            "UPDATE stock_purchases SET trash = 1 WHERE id = %s",
            (id,)
        )
        mysql.connection.commit()
        cursor.close()

        execution_time = time.time() - start_time
        return jsonify({
            "message": "Stock purchase deleted successfully",
            "execution_time": execution_time
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500
