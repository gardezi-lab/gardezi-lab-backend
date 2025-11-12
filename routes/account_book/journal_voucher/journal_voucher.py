import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app
from flask_mysqldb import MySQL

voucher_bp = Blueprint('voucher', __name__, url_prefix='/api/journal_vouchers')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@voucher_bp.route('/', methods=['POST'])
def create_journal_voucher():
    try:
        mysql = current_app.mysql
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'JV')
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

        # Create next listing_voucher (e.g., JV-001, CRV-001)
        listing_voucher = f"{voucher_type}-{last_number + 1:03d}"

        # Insert into main journal_voucher
        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, narration, voucher_type, listing_voucher))

        voucher_id = cursor.lastrowid

        # Insert all entries
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)

            if not account_head_id:
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries 
                (journal_voucher_id, account_head_id, dr, cr,type, date)
                VALUES (%s, %s, %s, %s,%s, %s)
            """, (voucher_id, account_head_id, dr, cr,voucher_type, date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Journal Voucher created successfully",
            "voucher_id": voucher_id,
            "listing_voucher": listing_voucher,
            "voucher_type": voucher_type
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# -------------------- GET ALL -------------------- #
@voucher_bp.route('/', methods=['GET'])
def get_all_journal_vouchers():
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Read optional voucher_type query parameter
        voucher_type = request.args.get('voucher_type', None)

        #  Base query
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
        """

        params = []

        # If voucher_type provided, filter by it
        if voucher_type:
            query += " WHERE jv.voucher_type = %s"
            params.append(voucher_type.upper())

        query += """
            GROUP BY jv.id
            ORDER BY jv.id DESC
        """

        cursor.execute(query, params)
        vouchers = cursor.fetchall()
        cursor.close()

        return jsonify(vouchers), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


# -------------------- UPDATE (PUT) -------------------- #
@voucher_bp.route('/<int:id>', methods=['PUT'])
def update_journal_voucher(id):
    """
    Update an existing Journal Voucher and its entries.
    """
    try:
        mysql = current_app.mysql
        data = request.get_json()

        date = data.get('date')
        narration = data.get('narration')
        voucher_type = data.get('voucher_type', 'JV')
        entries = data.get('entries')

        if not date or not narration:
            return jsonify({"error": "Date and narration are required"}), 400

        if not entries or not isinstance(entries, list):
            return jsonify({"error": "Entries must be a valid list"}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if voucher exists
        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Journal Voucher not found"}), 404

        # --- Update main voucher info ---
        cursor.execute("""
            UPDATE journal_voucher
            SET date = %s, narration = %s, voucher_type = %s
            WHERE id = %s
        """, (date, narration, voucher_type.upper(), id))

        # --- Delete existing entries before re-inserting ---
        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))

        # --- Insert updated entries ---
        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)

            if not account_head_id:
                return jsonify({"error": "Each entry must have account_head_id"}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries
                (journal_voucher_id, account_head_id, dr, cr, type, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id, account_head_id, dr, cr, voucher_type.upper(), date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Journal Voucher updated successfully",
            "voucher_id": id,
            "voucher_type": voucher_type.upper()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# -------------------- DELETE -------------------- #
@voucher_bp.route('/<int:id>', methods=['DELETE'])
def delete_journal_voucher(id):
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            return jsonify({"message": "Journal Voucher not found"}), 404

        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))
        cursor.execute("DELETE FROM journal_voucher WHERE id = %s", (id,))

        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Journal Voucher deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- GET ALL -------------------- 
@voucher_bp.route('/all', methods=['GET'])
def get_all_journal_vouchers_with_entries():
    """
    Fetch all journal vouchers along with their related entries.
    """
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch all journal vouchers
        cursor.execute("SELECT id, date, narration FROM journal_voucher ORDER BY id DESC")
        vouchers = cursor.fetchall()

        result = []

        for voucher in vouchers:
            voucher_id = voucher["id"]

            # Fetch voucher entries with account head name
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
            """, (voucher_id,))
            entries = cursor.fetchall()

            result.append({
                "id": voucher_id,
                "date": voucher["date"],
                "narration": voucher["narration"],
                "entries": entries
            })

        cursor.close()

        return jsonify({
            "message": "All Journal Vouchers fetched successfully",
            "total": len(result),
            "data": result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- VOUCHER PRINT API -------------------- #
@voucher_bp.route('/print/<int:id>', methods=['GET'])
def print_voucher(id):
    """
    Fetch a single voucher (any type) with full printable details.
    """
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Step 1: Get main voucher info
        cursor.execute("""
            SELECT 
                id,
                date,
                narration,
                voucher_type,
                listing_voucher
            FROM journal_voucher
            WHERE id = %s
        """, (id,))
        voucher = cursor.fetchone()

        if not voucher:
            cursor.close()
            return jsonify({"message": "Voucher not found"}), 404

        #  Get all related entries/////////
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

        #  Prepare printable response
        printable_voucher = {
            "voucher_id": voucher["id"],
            "voucher_type": voucher["voucher_type"],
            "listing_voucher": voucher["listing_voucher"],
            "date": str(voucher["date"]),
            "narration": voucher["narration"],
            "entries": entries,
            "total_dr": sum(float(e["dr"]) for e in entries),
            "total_cr": sum(float(e["cr"]) for e in entries)
        }

        return jsonify({
            "message": "Voucher fetched successfully for print",
            "data": printable_voucher
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    






    # -------------------- LEDGER API -------------------- #
@voucher_bp.route('/ledger', methods=['GET'])
def get_ledger_report():
   
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get parameters from request
        account_head_id = request.args.get('account_head_id', type=int)
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        # Fetch ledger entries
        cursor.execute("""
            SELECT *FROM journal_voucher_entries WHERE account_head_id = %s
              AND date BETWEEN %s AND %s
            ORDER BY date ASC
        """, (account_head_id, from_date, to_date))

        entries = cursor.fetchall()

        cursor.execute("""
            SELECT name_head FROM account_heads WHERE id = %s
        """, (account_head_id,))

        entriesh = cursor.fetchone()

        # Calculate totals
        total_dr = sum(float(e["dr"] or 0) for e in entries)
        total_cr = sum(float(e["cr"] or 0) for e in entries)

        cursor.close()

        # Return JSON response
        return jsonify({
            "message": "Ledger fetched successfully",
            "account_head_id": account_head_id,
            "account_head_name": entriesh['name_head'],
            "from_date": from_date,
            "to_date": to_date,
            "total_dr": total_dr,
            "total_cr": total_cr,
            "entries": entries
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
