from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
import time

cash_bp = Blueprint('cash', __name__, url_prefix='/api/cash')
mysql = MySQL()

#----------------- GET data from cash table ----------------

@cash_bp.route("/")
def get_data_cash():
    start_time = time.time()
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        
        filters = []
        params = []
        
        
        if from_date and to_date:
            filters.append("DATE(date) BETWEEN %s AND %s")
            params.extend([from_date, to_date])
        elif from_date:
            filters.append("DATE(date) >= %s")
            params.append(from_date)
        elif to_date:
            filters.append("DATE(date) <= %s")
            params.append(to_date)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = f"SELECT id, description, dr,cr,date FROM cash {where_clause} "
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        end_time = time.time()

        return jsonify({"message": "data is fetched successfuly","result": result,
                        "executionTime": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)})