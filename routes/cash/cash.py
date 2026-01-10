from flask import Flask, request, jsonify, Blueprint, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
import time
import math
cash_bp = Blueprint('cash', __name__, url_prefix='/api/cash')
mysql = MySQL()

#----------------- GET data from cash table ----------------

@cash_bp.route("/", methods=["GET"])
@token_required
def get_data_cash():
    start_time = time.time()
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 🔹 Query params
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 30, type=int)

        offset = (current_page - 1) * record_per_page

        filters = []
        params = []

        # 🔹 Date filters
        if from_date and to_date:
            filters.append("DATE(date) BETWEEN %s AND %s")
            params.extend([from_date, to_date])
        elif from_date:
            filters.append("DATE(date) >= %s")
            params.append(from_date)
        elif to_date:
            filters.append("DATE(date) <= %s")
            params.append(to_date)

        # 🔹 Search filter (sirf description)
        if search:
            filters.append("description LIKE %s")
            params.append(f"%{search}%")

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        # 🔹 Base query
        base_query = f"""
            SELECT id, description, dr, cr, date
            FROM cash
            {where_clause}
        """

        # 🔹 Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()["total"]

        # 🔹 Pagination + order
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([record_per_page, offset])

        cursor.execute(base_query, params)
        result = cursor.fetchall()

        cursor.close()
        end_time = time.time()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": result,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTime": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

