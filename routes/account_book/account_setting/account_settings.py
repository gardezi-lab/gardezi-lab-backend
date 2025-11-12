import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

account_settings_bp = Blueprint('default', __name__, url_prefix='/api/default')
mysql = MySQL()

@account_settings_bp.route('/<int:id>', methods=['PUT'])
def update_default_values(id):
    try:
        mysql = current_app.mysql
        data = request.get_json()

        default_cash = data.get('default_cash')
        default_bank = data.get('default_bank')
        default_stock_account = data.get('default_stock_account')  

        # Validate at least one field
        if default_cash is None and default_bank is None and default_stock_account is None:
            return jsonify({"error": "At least one field is required"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if record exists
        cursor.execute("SELECT * FROM account_setting WHERE id = %s", (id,))
        record = cursor.fetchone()
        if not record:
            cursor.close()
            return jsonify({"message": "Record not found"}), 404

        #  Validate IDs exist in account_head
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

        # Update record
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

        return jsonify({
            "message": "Record updated successfully",
            "id": id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



    # -------------------- GET -------------------- #

    
@account_settings_bp.route('/<int:id>', methods=['GET'])
def get_default_values(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Fetch account_setting record
        cursor.execute("SELECT * FROM account_setting WHERE id = %s", (id,))
        record = cursor.fetchone()
        if not record:
            cursor.close()
            return jsonify({"message": "Record not found"}), 404

        #  List of fields to fetch names for
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

        return jsonify({
            "message": "Record fetched successfully",
            "data": record
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
