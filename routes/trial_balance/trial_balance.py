import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL
import time
import math
trial_balance_report_bp = Blueprint(
    'trial_balance_report', __name__, url_prefix='/api/trial_balance'
)

mysql = MySQL()


# -------------------- CREATE TRIAL BALANCE  -------------------- #
@trial_balance_report_bp.route('/', methods=['POST'])
def create_trial_balance():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        data = request.get_json()

        account_id = data.get('account_id')
        debit = data.get('debit', 0)
        credit = data.get('credit', 0)
        date = data.get('date')

        if not account_id or not date:
            return jsonify({"error": "account_id and date required"}), 400

        if debit and credit:
            return jsonify({"error": "Account cannot have both debit & credit"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM account_heads WHERE id=%s", (account_id,))
        account = cursor.fetchone()
        if not account:
            return jsonify({"error": "Invalid account_id"}), 400

        cursor.execute(
            """
            INSERT INTO trial_balance_reporting (account_id, debit, credit, date)
            VALUES (%s, %s, %s, %s)
            """,
            (account_id, debit, credit, date)
        )
        mysql.connection.commit()
        entry_id = cursor.lastrowid
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "message": "Created",
            "id": entry_id,
            "account_id": account_id,
            "debit": debit,
            "credit": credit,
            "date": date,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500

# -------------------- GET TRIAL BALANCE -------------------- #
@trial_balance_report_bp.route('/', methods=['GET'])
def get_trial_balance():
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        from_date = request.args.get('from', '')
        to_date = request.args.get('to', '')
        search = request.args.get('search', '', type=str)
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 30, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base Query ---------------- #
        base_query = """
            FROM trial_balance_reporting tbr
            LEFT JOIN account_heads ah ON ah.id = tbr.account_id
            WHERE 1=1
        """
        values = []

        # ---------------- Date Filter ---------------- #
        if from_date and to_date:
            base_query += " AND tbr.date BETWEEN %s AND %s"
            values.extend([from_date, to_date])

        # ---------------- Search Filter ---------------- #
        if search:
            base_query += " AND ah.name_head LIKE %s"
            values.append(f"%{search}%")

        # ---------------- Count Total Records ---------------- #
        count_query = f"""
            SELECT COUNT(DISTINCT ah.name_head) AS total
            {base_query}
        """
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()['total'] or 0

        # ---------------- Grand Totals (Without Pagination) ---------------- #
        total_query = f"""
            SELECT 
                IFNULL(SUM(tbr.debit), 0) AS total_debit,
                IFNULL(SUM(tbr.credit), 0) AS total_credit
            {base_query}
        """
        cursor.execute(total_query, values)
        totals = cursor.fetchone()

        grand_total_debit = float(totals['total_debit'])
        grand_total_credit = float(totals['total_credit'])
        difference = grand_total_debit - grand_total_credit

        # ---------------- Paginated Data ---------------- #
        data_query = f"""
            SELECT 
                ah.name_head AS account_title,
                FORMAT(SUM(tbr.debit), 2) AS debit,
                FORMAT(SUM(tbr.credit), 2) AS credit
            {base_query}
            GROUP BY ah.name_head
            ORDER BY ah.name_head ASC
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
            "trial_balance": entries,
            "total_debit": grand_total_debit,
            "total_credit": grand_total_credit,
            "difference": difference,
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



# -------------------- GET BY ID -------------------- #
@trial_balance_report_bp.route('/entry/<int:id>', methods=['GET'])
def get_single_entry(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute(
            """
            SELECT 
                tbr.*, 
                ah.name_head AS account_title
            FROM trial_balance_reporting tbr
            LEFT JOIN account_heads ah ON ah.id = tbr.account_id
            WHERE tbr.id = %s
            """,
            (id,)
        )
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
