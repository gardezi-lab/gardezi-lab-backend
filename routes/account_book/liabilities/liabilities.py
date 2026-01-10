import MySQLdb.cursors
import math, time
from flask import Blueprint, jsonify, current_app, request

liabilities_bp = Blueprint('liabilities', __name__, url_prefix='/api/liabilities')

@liabilities_bp.route('/', methods=['GET'])
def get_all_account_heads():
    start_time = time.time()
    cursor = None

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 30, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base WHERE ---------------- #
        where_clause = "WHERE 1=1"
        values = []

        if search:
            where_clause += " AND name_head LIKE %s"
            values.append(f"%{search}%")

        # ---------------- Count Query ---------------- #
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM account_heads
            {where_clause}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"] or 0

        # ---------------- Data Query ---------------- #
        data_query = f"""
            SELECT 
                id,
                name_head
            FROM account_heads
            {where_clause}
            ORDER BY name_head ASC
            LIMIT %s OFFSET %s
        """
        data_values = values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        data = cursor.fetchall()
        end_time = time.time()

        execution_time = end_time - start_time
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1

        return jsonify({
            "data": data,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": execution_time
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
        }), 500

    finally:
        if cursor:
            cursor.close()
