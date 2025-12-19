import MySQLdb.cursors
import math, time
from flask import Blueprint, jsonify, current_app, request
from routes.authentication.authentication import token_required
inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@inventory_bp.route('/all', methods=['GET'])
@token_required
def get_all_inventory():
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base Query ---------------- #
        where_clause = "WHERE 1=1"
        values = []

        if search:
            where_clause += " AND si.name LIKE %s"
            values.append(f"%{search}%")

        # ---------------- Count Total Records ---------------- #
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM stock_items si
            {where_clause}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()['total'] or 0

        # ---------------- Paginated Inventory Data ---------------- #
        data_query = f"""
            SELECT 
                si.id AS item_id,
                si.name AS item_name,
                COALESCE(SUM(sp.qty), 0) - COALESCE(SUM(su.qty), 0) AS remaining_qty
            FROM stock_items si
            LEFT JOIN stock_purchases sp ON sp.stock_item_id = si.id
            LEFT JOIN stock_usage su ON su.stock_item_id = si.id
            {where_clause}
            GROUP BY si.id
            ORDER BY si.id ASC
            LIMIT %s OFFSET %s
        """
        data_values = values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        inventory_list = cursor.fetchall()

        cursor.close()

        # ---------------- Pagination ---------------- #
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1
        execution_time = time.time() - start_time

        return jsonify({
            "message": "All inventory items fetched successfully",
            "data": inventory_list,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": execution_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
