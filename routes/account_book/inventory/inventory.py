import MySQLdb.cursors
from flask import Blueprint, jsonify, current_app

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@inventory_bp.route('/all', methods=['GET'])
def get_all_inventory():
    """
    Sare inventory items + remaining stock show karne ka route
    """
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM stock_items ORDER BY id ASC")
        items = cursor.fetchall()

        inventory_list = []

        for item in items:
            item_id = item['id']
            item_name = item['name']

            # Total purchase qty
            cursor.execute("""
                SELECT COALESCE(SUM(qty), 0) AS total_purchase
                FROM stock_purchases
                WHERE stock_item_id = %s
            """, (item_id,))
            total_purchase = cursor.fetchone()['total_purchase']

            # Total usage qty
            cursor.execute("""
                SELECT COALESCE(SUM(qty), 0) AS total_usage
                FROM stock_usage
                WHERE stock_item_id = %s
            """, (item_id,))
            total_usage = cursor.fetchone()['total_usage']

            # Remaining stock
            remaining_qty = total_purchase - total_usage

            inventory_list.append({
                "item_id": item_id,
                "item_name": item_name,
                # "total_purchased": total_purchase,
                # "total_used": total_usage,
                "remaining_qty": remaining_qty
            })

        cursor.close()

        return jsonify({
            "message": "All inventory items fetched successfully",
            "total": len(inventory_list),
            "data": inventory_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500