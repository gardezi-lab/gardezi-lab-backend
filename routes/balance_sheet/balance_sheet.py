import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
import time
import math

balance_sheet_report_bp = Blueprint(
    'balance_sheet_report', __name__, url_prefix='/api/balance_sheet'
)
mysql = MySQL()


# -------------------- CREATE POST -------------------- #
@balance_sheet_report_bp.route('/', methods=['POST'])
@token_required
def create_balance_sheet_entry():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        account_name = data.get('account_name')
        entry_type = data.get('type')
        amount = data.get('amount')
        date = data.get('date')

        if not all([account_name, entry_type, amount, date]):
            return jsonify({"error": "Missing required fields"}), 400

        if entry_type not in ['asset', 'liability', 'equity']:
            return jsonify({"error": "Invalid type. Must be asset, liability or equity"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "INSERT INTO balance_sheet_reporting (account_name, type, amount, date) VALUES (%s, %s, %s, %s)",
            (account_name, entry_type, amount, date)
        )
        mysql.connection.commit()

        entry_id = cursor.lastrowid
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "message": "Created",
            "id": entry_id,
            "account_name": account_name,
            "type": entry_type,
            "amount": amount,
            "date": date,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500


# -------------------- GET BALANCE SHEET -------------------- #
@balance_sheet_report_bp.route('/', methods=['GET'])
@token_required
def get_all_balance_sheet():
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        from_date = request.args.get('from', '')
        to_date = request.args.get('to', '')
        search = request.args.get('search', '', type=str)
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 10, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base Query ---------------- #
        base_query = """
            FROM balance_sheet_reporting
            WHERE 1=1
        """
        values = []

        # ---------------- Date Filter ---------------- #
        if from_date and to_date:
            base_query += " AND date BETWEEN %s AND %s"
            values.extend([from_date, to_date])

        # ---------------- Search Filter ---------------- #
        if search:
            base_query += " AND account_name LIKE %s"
            values.append(f"%{search}%")

        # ---------------- Count Total Records ---------------- #
        count_query = f"""
            SELECT COUNT(*) AS total
            {base_query}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()['total'] or 0

        # ---------------- Grand Totals (Without Pagination) ---------------- #
        total_query = f"""
            SELECT 
                IFNULL(SUM(CASE WHEN type = 'asset' THEN amount ELSE 0 END), 0) AS total_assets,
                IFNULL(SUM(CASE WHEN type = 'liability' THEN amount ELSE 0 END), 0) AS total_liabilities,
                IFNULL(SUM(CASE WHEN type = 'equity' THEN amount ELSE 0 END), 0) AS total_equity
            {base_query}
        """
        cursor.execute(total_query, values)
        totals = cursor.fetchone()

        total_assets = float(totals['total_assets'])
        total_liabilities = float(totals['total_liabilities'])
        total_equity = float(totals['total_equity'])
        balance = total_assets - total_liabilities - total_equity

        # ---------------- Paginated Data ---------------- #
        data_query = f"""
            SELECT 
                id,
                date,
                type,
                account_name,
                FORMAT(amount, 2) AS amount
            {base_query}
            ORDER BY type ASC, account_name ASC
            LIMIT %s OFFSET %s
        """
        paginated_values = values + [record_per_page, offset]
        cursor.execute(data_query, paginated_values)
        entries = cursor.fetchall()

        cursor.close()

        # ---------------- Pagination ---------------- #
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1
        execution_time = time.time() - start_time

        return jsonify({
            "from_date": from_date,
            "to_date": to_date,
            "entries": entries,
            "totals": {
                "assets": total_assets,
                "liabilities": total_liabilities,
                "equity": total_equity,
                "balance": balance
            },
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": execution_time
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({
            "error": str(e),
            "execution_time": execution_time
        }), 500



# -------------------- GET BY ID  -------------------- #
@balance_sheet_report_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_balance_sheet_entry(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM balance_sheet_reporting WHERE id = %s", (id,))
        entry = cursor.fetchone()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        if not entry:
            return jsonify({"message": "Not found", "execution_time": execution_time}), 404

        return jsonify({"data": entry, "execution_time": execution_time}), 200

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500


# -------------------- UPDATE PUT -------------------- #
@balance_sheet_report_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_balance_sheet_entry(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM balance_sheet_reporting WHERE id = %s", (id,))
        if not cursor.fetchone():
            end_time = time.time()
            execution_time = end_time - start_time
            return jsonify({"message": "Not found", "execution_time": execution_time}), 404

        account_name = data.get('account_name')
        entry_type = data.get('type')
        amount = data.get('amount')
        date = data.get('date')

        if not all([account_name, entry_type, amount, date]):
            return jsonify({"error": "Missing required fields"}), 400

        if entry_type not in ['asset', 'liability', 'equity']:
            return jsonify({"error": "Invalid type"}), 400

        cursor.execute(
            "UPDATE balance_sheet_reporting SET account_name=%s, type=%s, amount=%s, date=%s WHERE id=%s",
            (account_name, entry_type, amount, date, id)
        )
        mysql.connection.commit()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"message": "Updated", "execution_time": execution_time}), 200

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500




