import time
import math
import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL

cash_receipt_bp = Blueprint('cash_receipt', __name__, url_prefix='/cash_receipt_voucher')
mysql = MySQL()


# -------------------- CREATE (POST) -------------------- #
@cash_receipt_bp.route('/', methods=['POST'])
@token_required
def create_cash_receipt_voucher():
    start_time = time.time()  # ---- TIME START ----

    try:
        mysql = current_app.mysql  
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'CRV')
        entries = data.get('entries')

        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400
        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        voucher_type = voucher_type.upper()

        cursor.execute("""
            SELECT listing_voucher 
            FROM journal_voucher 
            WHERE voucher_type = %s 
            ORDER BY id DESC 
            LIMIT 1
        """, (voucher_type,))
        last_voucher = cursor.fetchone()

        if last_voucher and last_voucher["listing_voucher"]:
            try:
                last_number = int(last_voucher["listing_voucher"].split('-')[1])
            except (IndexError, ValueError):
                last_number = 0
        else:
            last_number = 0

        listing_voucher = f"{voucher_type}-{last_number + 1:03d}"

        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, narration, voucher_type, listing_voucher))
        voucher_id = cursor.lastrowid

        cursor.execute("SELECT default_cash FROM account_setting WHERE id = 1")
        record = cursor.fetchone()

        if not record or not record['default_cash']:
            return jsonify({"error": "Default cash account not set in account_setting"}), 500

        default_cash_id = record['default_cash']

        total_cr = 0
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)
            total_cr += cr

            if not account_head_id:
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries 
                (journal_voucher_id, account_head_id, dr, cr, type, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (voucher_id, account_head_id, dr, cr, voucher_type, date))

        cursor.execute("""
            INSERT INTO journal_voucher_entries 
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_id, default_cash_id, total_cr, 0, voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        end_time = time.time()  # ---- TIME END ----
        execution_time = end_time - start_time

        return jsonify({
            "message": "Cash Receipt Voucher created successfully",
            "voucher_id": voucher_id,
            "listing_voucher": listing_voucher,
            "voucher_type": voucher_type,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET ALL (Pagination + Filter) -------------------- #
@cash_receipt_bp.route('/', methods=['GET'])
@token_required
def get_all_cash_receipt_vouchers():
    start_time = time.time()

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base WHERE Clause ---------------- #
        where_clause = "WHERE jv.voucher_type = 'CRV'"
        filter_values = []

        # ---------------- Filtering ---------------- #
        if search:
            where_clause += """
                AND (
                    jv.narration LIKE %s
                    OR jv.listing_voucher LIKE %s
                    OR DATE_FORMAT(jv.date, '%Y-%m-%d') LIKE %s
                )
            """
            filter_values.extend([f"%{search}%"] * 3)

        # ---------------- Count Total Records ---------------- #
        count_query = f"""
            SELECT COUNT(DISTINCT jv.id) AS total
            FROM journal_voucher AS jv
            LEFT JOIN journal_voucher_entries AS jve
                ON jv.id = jve.journal_voucher_id
            {where_clause}
        """
        cursor.execute(count_query, filter_values)
        total_records = cursor.fetchone()["total"] or 0

        # ---------------- Fetch Paginated Data ---------------- #
        data_query = f"""
            SELECT 
                jv.id,
                jv.date,
                jv.narration,
                jv.voucher_type,
                jv.listing_voucher,
                COUNT(jve.id) AS total_entries
            FROM journal_voucher AS jv
            LEFT JOIN journal_voucher_entries AS jve
                ON jv.id = jve.journal_voucher_id
            {where_clause}
            GROUP BY jv.id
            ORDER BY jv.id DESC
            LIMIT %s OFFSET %s
        """
        data_values = filter_values + [record_per_page, offset]
        cursor.execute(data_query, data_values)
        vouchers = cursor.fetchall()
        cursor.close()

        # ---------------- Pagination Calculation ---------------- #
        total_pages = math.ceil(total_records / record_per_page) if record_per_page else 1
        execution_time = time.time() - start_time

        return jsonify({
            "execution_time": execution_time,
            "data": vouchers,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





# -------------------- GET BY ID -------------------- #
@cash_receipt_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_cash_receipt_voucher_by_id(id):
    start_time = time.time()

    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("""
            SELECT id, date, narration, listing_voucher, voucher_type 
            FROM journal_voucher 
            WHERE id = %s AND voucher_type = 'CRV'
        """, (id,))
        voucher = cursor.fetchone()

        if not voucher:
            cursor.close()
            return jsonify({"message": "Cash Receipt Voucher not found"}), 404

        cursor.execute("""
            SELECT 
                jve.id,
                jve.account_head_id,
                ah.name_head AS account_head_name,
                jve.dr,
                jve.cr
            FROM journal_voucher_entries AS jve
            LEFT JOIN account_heads AS ah ON jve.account_head_id = ah.id
            WHERE jve.journal_voucher_id = %s
        """, (id,))
        entries = cursor.fetchall()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        voucher["entries"] = entries
        voucher["execution_time"] = execution_time

        return jsonify(voucher), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# -------------------- DELETE -------------------- #
@cash_receipt_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_cash_receipt_voucher(id):
    start_time = time.time()

    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s AND voucher_type = 'CRV'", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Cash Receipt Voucher not found"}), 404

        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))
        cursor.execute("DELETE FROM journal_voucher WHERE id = %s", (id,))

        mysql.connection.commit()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "message": "Cash Receipt Voucher deleted successfully",
            "execution_time": execution_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
