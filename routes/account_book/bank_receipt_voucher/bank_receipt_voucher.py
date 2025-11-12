import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

# Blueprint setup
bank_receipt_voucher_bp = Blueprint('bank_receipt_voucher', __name__, url_prefix='/api/bank_receipt_voucher')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@bank_receipt_voucher_bp.route('/', methods=['POST'])
def create_bank_receipt_voucher():
    """
    Create a new Bank Receipt Voucher (BRV)
    """
    try:
        mysql = current_app.mysql
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'BRV') 
        entries = data.get('entries')

        # ---- Validation ----
        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400

        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        voucher_type = voucher_type.upper()

        # ---- Generate next listing_voucher ----
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

        # ---- Insert main voucher record ----
        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, narration, voucher_type, listing_voucher))
        voucher_id = cursor.lastrowid

        # ---- Get default bank account ----
        cursor.execute("SELECT default_bank FROM account_setting WHERE id = 1")
        record = cursor.fetchone()

        if not record or not record['default_bank']:
            cursor.close()
            return jsonify({"error": "Default bank account not set in account_setting"}), 500

        default_bank_id = record['default_bank']

        # ---- Insert all credit entries ----
        total_cr = 0
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)
            total_cr += cr

            if not account_head_id:
                cursor.close()
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            # Insert each entry
            cursor.execute("""
                INSERT INTO journal_voucher_entries
                (journal_voucher_id, account_head_id, dr, cr, type, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (voucher_id, account_head_id, dr, cr, voucher_type, date))

        # ---- Insert the default bank account entry (Dr entry) ----
        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_id, default_bank_id, total_cr, 0, voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Bank Receipt Voucher created successfully",
            "voucher_id": voucher_id,
            "listing_voucher": listing_voucher,
            "voucher_type": voucher_type,
            "date": date,
            "type": voucher_type
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# -------------------- UPDATE (PUT) -------------------- #
@bank_receipt_voucher_bp.route('/<int:id>', methods=['PUT'])
def update_cash_receipt_voucher(id):
    """
    Update an existing Cash Receipt Voucher (CRV)
    """
    try:
        mysql = current_app.mysql
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'CRV')
        entries = data.get('entries')

        # ---- Validation ----
        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400

        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        voucher_type = voucher_type.upper()

        # ---- Check if voucher exists ----
        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Cash Receipt Voucher not found"}), 404

        # ---- Update main voucher record ----
        cursor.execute("""
            UPDATE journal_voucher
            SET date = %s, narration = %s, voucher_type = %s
            WHERE id = %s
        """, (date, narration, voucher_type, id))

        # ---- Remove all existing entries before re-inserting ----
        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))

        # ---- Get default cash account ----
        cursor.execute("SELECT default_cash FROM account_setting WHERE id = 1")
        record = cursor.fetchone()

        if not record or not record['default_cash']:
            return jsonify({"error": "Default cash account not set in account_setting"}), 500

        default_cash_id = record['default_cash']

        # ---- Insert updated credit entries ----
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
            """, (id, account_head_id, dr, cr, voucher_type, date))

        # ---- Insert the default cash account (Dr entry) ----
        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, default_cash_id, total_cr, 0, voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Cash Receipt Voucher updated successfully",
            "voucher_id": id,
            "voucher_type": voucher_type
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





# -------------------- UPDATE (PUT) -------------------- #
@bank_receipt_voucher_bp.route('/<int:id>', methods=['PUT'])
def update_bank_receipt_voucher(id):
    """
    Update an existing Bank Receipt Voucher (BRV)
    """
    try:
        mysql = current_app.mysql
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'BRV')
        entries = data.get('entries')

        # ---- Validation ----
        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400

        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        voucher_type = voucher_type.upper()

        # ---- Check if voucher exists ----
        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Bank Receipt Voucher not found"}), 404

        # ---- Update main voucher record ----
        cursor.execute("""
            UPDATE journal_voucher
            SET date = %s, narration = %s, voucher_type = %s
            WHERE id = %s
        """, (date, narration, voucher_type, id))

      

        # ---- Get default bank account ----
        cursor.execute("SELECT default_bank FROM account_setting WHERE id = 1")
        record = cursor.fetchone()

        if not record or not record['default_bank']:
            return jsonify({"error": "Default bank account not set in account_setting"}), 500

        default_bank_id = record['default_bank']

        # ---- Insert updated credit entries ----
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
            """, (id, account_head_id, dr, cr, voucher_type, date))

        # ---- Insert the default bank account ----
        cursor.execute("""
            INSERT INTO journal_voucher_entries
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, default_bank_id, total_cr, 0, voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Bank Receipt Voucher updated successfully",
            "voucher_id": id,
            "voucher_type": voucher_type
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
