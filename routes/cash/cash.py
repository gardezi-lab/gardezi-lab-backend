from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL


cash_bp = Blueprint('cash', __name__, url_prefix='/api/cash')
mysql = MySQL()

#----------------- GET data from cash table ----------------

@cash_bp.route("/")
def get_data_cash():
    try:
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM cash"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return jsonify({"message": "data is fetched successfuly",
                        "result": result})
    except Exception as e:
        return jsonify({"error": str(e)})