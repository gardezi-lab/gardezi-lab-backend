import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL
import time
from routes.authentication.authentication import token_required

account_settings_bp = Blueprint('default', __name__, url_prefix='/api/default')
mysql = MySQL()

@account_settings_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_default_values(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        default_cash = data.get('default_cash')
        default_bank = data.get('default_bank')
        default_stock_account = data.get('default_stock_account')  

        if default_cash is None and default_bank is None and default_stock_account is None:
            return jsonify({"error": "At least one field is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM account_setting WHERE id = %s", (id,))
        record = cursor.fetchone()
        if not record:
            cursor.close()
            return jsonify({"message": "Record not found"}), 404

        for field_name, field_value in [
            ("default_cash", default_cash),
            ("default_bank", default_bank),
            ("default_stock_account", default_stock_account)
        ]:
            if field_value is not None:
                cursor.execute("SELECT id FROM account_heads WHERE id = %s", (field_value,))
                head = cursor.fetchone()
                if not head:
                    cursor.close()
                    return jsonify({"error": f"{field_name} {field_value} does not exist in account_head"}), 400

        cursor.execute("""
            UPDATE account_setting
            SET 
                default_cash = COALESCE(%s, default_cash),
                default_bank = COALESCE(%s, default_bank),
                default_stock_account = COALESCE(%s, default_stock_account)
            WHERE id = %s
        """, (default_cash, default_bank, default_stock_account, id))

        mysql.connection.commit()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "message": "Record updated successfully",
            "id": id,
            "time_calculated": execution_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# -------------------- GET -------------------- #

@account_settings_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_default_values(id):
    start_time = time.time()   
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM account_setting WHERE id = %s", (id,))
        record = cursor.fetchone()
        if not record:
            cursor.close()
            return jsonify({"message": "Record not found"}), 404

        head_fields = ['default_cash', 'default_bank', 'default_stock_account']

        for field in head_fields:
            head_id = record.get(field)
            if head_id:
                cursor.execute("SELECT name_head FROM account_heads WHERE id = %s", (head_id,))
                result = cursor.fetchone()
                record[f"{field}_name"] = result['name_head'] if result else None
            else:
                record[f"{field}_name"] = None

        cursor.close()

        end_time = time.time()                 
        execution_time = end_time - start_time   

        return jsonify({
            "message": "Record fetched successfully",
            "data": record,
            "time_calculated": execution_time   
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
