import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

stock_usage_bp = Blueprint('stock_usage', __name__, url_prefix='/api/stock_usage')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_usage_bp.route('/', methods=['POST'])
def create_stock_usage():
    try:
        mysql = current_app.mysql
        data = request.get_json()

        stock_item_id = data.get('stock_item_id')
        qty = data.get('qty')

        if not stock_item_id or not qty:
            return jsonify({"error": "stock_item_id and qty are required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO stock_usage (stock_item_id, qty)
            VALUES (%s, %s)
        """, (stock_item_id, qty))
        mysql.connection.commit()
        usage_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            "message": "Stock usage created successfully",
            "usage_id": usage_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ALL (GET) -------------------- #
@stock_usage_bp.route('/', methods=['GET'])
def get_all_stock_usage():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT su.id, si.name AS item_name, su.qty
            FROM stock_usage su
            JOIN stock_items si ON su.stock_item_id = si.id
            ORDER BY su.id DESC
        """)
        usage = cursor.fetchall()
        cursor.close()

        return jsonify(usage), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ONE (GET by ID) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['GET'])
def get_stock_usage(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT su.id, si.name AS item_name, su.qty
            FROM stock_usage su
            JOIN stock_items si ON su.stock_item_id = si.id
            WHERE su.id = %s
        """, (id,))
        usage = cursor.fetchone()
        cursor.close()

        if not usage:
            return jsonify({"message": "Stock usage not found"}), 404

        return jsonify(usage), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- UPDATE (PUT) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['PUT'])
def update_stock_usage(id):
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
            return jsonify({"message": "Stock usage not found"}), 404

        cursor.execute("""
            UPDATE stock_usage
            SET stock_item_id = %s, qty = %s
            WHERE id = %s
        """, (stock_item_id, qty, id))

        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock usage updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- DELETE (DELETE) -------------------- #
@stock_usage_bp.route('/<int:id>', methods=['DELETE'])
def delete_stock_usage(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_usage WHERE id = %s", (id,))
        usage = cursor.fetchone()

        if not usage:
            cursor.close()
            return jsonify({"message": "Stock usage not found"}), 404

        cursor.execute("DELETE FROM stock_usage WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock usage deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




