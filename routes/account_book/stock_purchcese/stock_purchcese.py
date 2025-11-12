# stock_purchase_api.py
import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL
from datetime import datetime

# Blueprint
stock_purchase_bp = Blueprint('stock_purchase', __name__, url_prefix='/api/stock_purchases')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_purchase_bp.route('/', methods=['POST'])
def create_stock_purchase():
    try:
        mysql = current_app.mysql
        data = request.get_json()

        # Get data from request
        vendor_id = data.get('vendor_id')
        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')
        price = data.get('price')

        # Check required fields
        if not all([vendor_id, stock_item_id, qty, price]):
            return jsonify({"error": "All fields are required"}), 400

        # Convert qty and price to numbers
        qty = float(qty)
        price = float(price)
        totalamount = qty * price

        # Open cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get default stock account
        cursor.execute("SELECT default_stock_account FROM account_setting WHERE id = 1")
        record = cursor.fetchone()
        default_cash_id = record['default_stock_account']

        # Prepare date
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

        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_id, vendor_id, 0, totalamount, 'JV', date))

        # Insert stock purchase
        cursor.execute("""
            INSERT INTO stock_purchases (vendor_id, stock_item_id, qty, price)
            VALUES (%s, %s, %s, %s)
        """, (vendor_id, stock_item_id, qty, price))
        mysql.connection.commit()
        purchase_id = cursor.lastrowid

        cursor.close()

        return jsonify({
            "message": "Stock purchase created successfully",
            "purchase_id": purchase_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- READ ALL (GET) -------------------- #
@stock_purchase_bp.route('/', methods=['GET'])
def get_all_stock_purchases():
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
                sp.price
            FROM stock_purchases sp
            LEFT JOIN account_heads ah ON sp.vendor_id = ah.id
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            ORDER BY sp.id DESC
        """)
        purchases = cursor.fetchall()
        cursor.close()
        return jsonify(purchases), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ONE (GET by ID) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['GET'])
def get_stock_purchase(id):
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
                sp.price
            FROM stock_purchases sp
            LEFT JOIN account_heads ah ON sp.vendor_id = ah.id
            LEFT JOIN stock_items si ON sp.stock_item_id = si.id
            WHERE sp.id = %s
        """, (id,))
        purchase = cursor.fetchone()
        cursor.close()

        if not purchase:
            return jsonify({"message": "Stock purchase not found"}), 404

        return jsonify(purchase), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- UPDATE (PUT) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['PUT'])
def update_stock_purchase(id):
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
            return jsonify({"message": "Stock purchase not found"}), 404

        cursor.execute("""
            UPDATE stock_purchases
            SET vendor_id = %s, stock_item_id = %s, qty = %s, price = %s
            WHERE id = %s
        """, (vendor_id, stock_item_id, qty, price, id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock purchase updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- DELETE (DELETE) -------------------- #
@stock_purchase_bp.route('/<int:id>', methods=['DELETE'])
def delete_stock_purchase(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_purchases WHERE id = %s", (id,))
        purchase = cursor.fetchone()

        if not purchase:
            cursor.close()
            return jsonify({"message": "Stock purchase not found"}), 404

        cursor.execute("DELETE FROM stock_purchases WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock purchase deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500