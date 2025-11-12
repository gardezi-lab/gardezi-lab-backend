import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

stock_items_bp = Blueprint('stock_items', __name__, url_prefix='/api    ')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@stock_items_bp.route('/', methods=['POST'])
def create_stock_item():
    try:
        mysql = current_app.mysql
        data = request.get_json()

        name = data.get('name')

        if not name:
            return jsonify({"error": "Name is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO stock_items (name)
            VALUES (%s)
        """, (name,))
        mysql.connection.commit()
        item_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            "message": "Stock item created successfully",
            "item_id": item_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ALL (GET) -------------------- #
@stock_items_bp.route('/', methods=['GET'])
def get_all_stock_items():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_items ORDER BY id DESC")
        items = cursor.fetchall()
        cursor.close()

        return jsonify(items), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- READ ONE (GET by ID) -------------------- #
@stock_items_bp.route('/<int:id>', methods=['GET'])
def get_stock_item(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()
        cursor.close()

        if not item:
            return jsonify({"message": "Stock item not found"}), 404

        return jsonify(item), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- UPDATE (PUT) -------------------- #
@stock_items_bp.route('/<int:id>', methods=['PUT'])
def update_stock_item(id):
    try:
        mysql = current_app.mysql
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"error": "Name is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            return jsonify({"message": "Stock item not found"}), 404

        cursor.execute("""
            UPDATE stock_items
            SET name = %s
            WHERE id = %s
        """, (name, id))

        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock item updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- DELETE (DELETE) -------------------- #
@stock_items_bp.route('/<int:id>', methods=['DELETE'])
def delete_stock_item(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stock_items WHERE id = %s", (id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            return jsonify({"message": "Stock item not found"}), 404

        cursor.execute("DELETE FROM stock_items WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Stock item deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
