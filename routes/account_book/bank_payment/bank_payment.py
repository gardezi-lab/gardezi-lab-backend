import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

# -------------------- BLUEPRINT SETUP -------------------- #
bank_payment_bp = Blueprint('bank_payment', __name__, url_prefix='/api/bank_payment_voucher')
mysql = MySQL()


# -------------------- CREATE (POST) -------------------- #
@bank_payment_bp.route('/', methods=['POST'])
def create_bank_payment_voucher():
    try:
        mysql = current_app.mysql  
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'BPV')
        entries = data.get('entries')

        # ---- Basic validation ----
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
            return jsonify({"error": "Default bank account not set in account_setting"}), 500
        default_bank_id = record['default_bank']

        # ---- Insert all debit entries (BPV adds DR side) ----
        total_dr = 0
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)
            total_dr += dr

            if not account_head_id:
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries 
                (journal_voucher_id, account_head_id, dr, cr)
                VALUES (%s, %s, %s, %s)
            """, (voucher_id, account_head_id, dr, cr))

        # ---- Insert default bank account (credit entry) ----
        cursor.execute("""
            INSERT INTO journal_voucher_entries 
            (journal_voucher_id, account_head_id, dr, cr)
            VALUES (%s, %s, %s, %s)
        """, (voucher_id, default_bank_id, 0, total_dr))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Bank Payment Voucher created successfully",
            "voucher_id": voucher_id,
            "listing_voucher": listing_voucher,
            "voucher_type": voucher_type
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET ALL -------------------- #
@bank_payment_bp.route('/', methods=['GET'])
def get_all_bank_payment_vouchers():
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        query = """
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
            WHERE jv.voucher_type = 'BPV'
            GROUP BY jv.id
            ORDER BY jv.id DESC
        """
        cursor.execute(query)
        vouchers = cursor.fetchall()
        cursor.close()

        return jsonify(vouchers), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET BY ID -------------------- #
@bank_payment_bp.route('/<int:id>', methods=['GET'])
def get_bank_payment_voucher_by_id(id):
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("""
            SELECT id, date, narration, listing_voucher, voucher_type 
            FROM journal_voucher 
            WHERE id = %s AND voucher_type = 'BPV'
        """, (id,))
        voucher = cursor.fetchone()

        if not voucher:
            cursor.close()
            return jsonify({"message": "Bank Payment Voucher not found"}), 404

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

        voucher["entries"] = entries
        return jsonify(voucher), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- DELETE -------------------- #
@bank_payment_bp.route('/<int:id>', methods=['DELETE'])
def delete_bank_payment_voucher(id):
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s AND voucher_type = 'BPV'", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Bank Payment Voucher not found"}), 404

        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))
        cursor.execute("DELETE FROM journal_voucher WHERE id = %s", (id,))

        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Bank Payment Voucher deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


# -------------------- UPDATE (PUT) -------------------- #
@bank_payment_bp.route('/<int:id>', methods=['PUT'])
def update_bank_payment_voucher(id):
    """
    Update an existing Bank Payment Voucher (BPV)
    """
    try:
        mysql = current_app.mysql  
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'BPV')
        entries = data.get('entries')

        # ---- Validation ----
        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400

        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        voucher_type = voucher_type.upper()

        # ---- Check if the voucher exists ----
        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s AND voucher_type = %s", (id, voucher_type))
        voucher = cursor.fetchone()

        if not voucher:
            cursor.close()
            return jsonify({"message": "Bank Payment Voucher not found"}), 404

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

        # ---- Reinsert all debit entries ----
        total_dr = 0
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)
            total_dr += dr

            if not account_head_id:
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries 
                (journal_voucher_id, account_head_id, dr, cr, type, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id, account_head_id, dr, cr, voucher_type, date))

        # ---- Insert default bank account (credit entry) ----
        cursor.execute("""
            INSERT INTO journal_voucher_entries 
            (journal_voucher_id, account_head_id, dr, cr, type, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, default_bank_id, 0, total_dr, voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Bank Payment Voucher updated successfully",
            "voucher_id": id,
            "voucher_type": voucher_type
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
