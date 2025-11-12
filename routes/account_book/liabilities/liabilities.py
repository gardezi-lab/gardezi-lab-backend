import MySQLdb.cursors
from flask import Blueprint, jsonify, current_app
from flask_mysqldb import MySQL

liabilities_bp = Blueprint('liabilities', __name__, url_prefix='/api/liabilities')
mysql = MySQL()

@liabilities_bp.route('/', methods=['GET'])
def get_all_account_heads():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Only id and name_head for dropdown
        cursor.execute("SELECT id, name_head FROM account_heads")
        data = cursor.fetchall()
        cursor.close()

        if not data:
            return jsonify({"message": "Koi account_head nahi mila"}), 404

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    