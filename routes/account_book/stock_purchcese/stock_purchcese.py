import time
import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
from datetime import datetime
import math

stock_purchase_bp = Blueprint(
    'stock_purchase', __name__, url_prefix='/api/stock_purchases'
)
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

        # Journal voucher
        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, 'Stock Purchased', 'JV', ''))
        voucher_id = cursor.lastrowid

        # Debit entry only
        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_id, default_cash_id, totalamount, 0, 'JV', date))

        # Stock purchase insert 
        cursor.execute("""
            INSERT INTO stock_purchases (stock_item_id, qty, price, date_created)
            VALUES (%s, %s, %s, NOW())
        """, (stock_item_id, qty, price))

        mysql.connection.commit()
        purchase_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            "message": "Stock purchase created successfully",
            "purchase_id": purchase_id,
            "execution_time": time.time() - start_time
        }), 201

    except Exception as e:
        return jsonify({
            "error": str(e),
            "execution_time": time.time() - start_time
        }), 500


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
        record_per_page = request.args.get("recordperpage", 30, type=int)
        offset = (current_page - 1) * record_per_page

        where_clause = "WHERE sp.trash = 0"
        values = []

        if search:
            where_clause += " AND si.name LIKE %s"
            values.append(f"%{search}%")

        count_query = f"""
            SELECT COUNT(DISTINCT sp.id) AS total
            FROM stock_purchases sp
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            {where_clause}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"] or 0

        data_query = f"""
            SELECT 
                sp.id,
                sp.stock_item_id,
                si.name AS item_name,
                sp.qty,
                sp.price,
                sp.date_created
            FROM stock_purchases sp
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            {where_clause}
            ORDER BY sp.id DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, values + [record_per_page, offset])
        purchases = cursor.fetchall()

        return jsonify({
            "data": purchases,
            "totalRecords": total_records,
            "totalPages": math.ceil(total_records / record_per_page),
            "currentPage": current_page,
            "execution_time": time.time() - start_time
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "execution_time": time.time() - start_time
        }), 500
    finally:
        if cursor:
            cursor.close()


# -------------------- READ ONE -------------------- #
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
                sp.stock_item_id,
                si.name AS item_name,
                sp.qty,
                sp.price,
                sp.date_created
            FROM stock_purchases sp
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            WHERE sp.id = %s
        """, (id,))

        purchase = cursor.fetchone()
        cursor.close()

        if not purchase:
            return jsonify({"message": "Not found"}), 404

        return jsonify({
            "data": purchase,
            "execution_time": time.time() - start_time
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "execution_time": time.time() - start_time
        }), 500


# -------------------- UPDATE -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_stock_purchase(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')
        price = data.get('price')

        if not all([stock_item_id, qty, price]):
            return jsonify({"error": "All fields are required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM stock_purchases WHERE id=%s", (id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Not found"}), 404

        cursor.execute("""
            UPDATE stock_purchases
            SET stock_item_id=%s, qty=%s, price=%s
            WHERE id=%s
        """, (stock_item_id, qty, price, id))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Updated successfully",
            "execution_time": time.time() - start_time
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "execution_time": time.time() - start_time
        }), 500


# --------------------  (SOFT DELETE) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_stock_purchase(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute(
            "SELECT id FROM stock_purchases WHERE id=%s AND trash=0",
            (id,)
        )
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Not found"}), 404

        cursor.execute(
            "UPDATE stock_purchases SET trash=1 WHERE id=%s",
            (id,)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Deleted successfully",
            "execution_time": time.time() - start_time
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "execution_time": time.time() - start_time
        }), 500