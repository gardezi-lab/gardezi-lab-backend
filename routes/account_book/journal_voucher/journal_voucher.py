import MySQLdb.cursors
from flask import Blueprint, jsonify, request, current_app, make_response
from routes.authentication.authentication import token_required
from flask_mysqldb import MySQL
import os
import time
import math

voucher_bp = Blueprint('voucher', __name__, url_prefix='/api/journal_vouchers')
mysql = MySQL()

# -------------------- CREATE (POST) -------------------- #
@voucher_bp.route('/', methods=['POST'])
@token_required
def create_journal_voucher():
    start_time = time.time()
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

        listing_voucher = f"{voucher_type}-{last_number + 1:03d}"

        cursor.execute("""
            INSERT INTO journal_voucher (date, narration, voucher_type, listing_voucher)
            VALUES (%s, %s, %s, %s)
        """, (date, narration, voucher_type, listing_voucher))

        voucher_id = cursor.lastrowid

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

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "message": "Journal Voucher created successfully",
            "voucher_id": voucher_id,
            "listing_voucher": listing_voucher,
            "voucher_type": voucher_type,
            "execution_time": execution_time
        }), 201

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500


# -------------------- GET ALL -------------------- #
@voucher_bp.route('/', methods=['GET'])
@token_required
def get_all_journal_vouchers():
    start_time = time.time()
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # ---------------- Query Params ---------------- #
        voucher_type = request.args.get('voucher_type', None)
        search = request.args.get('search', "", type=str)
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 10, type=int)
        offset = (current_page - 1) * record_per_page

        # ---------------- Base Query ---------------- #
        base_query = """
            FROM journal_voucher AS jv
            LEFT JOIN journal_voucher_entries AS jve
                ON jv.id = jve.journal_voucher_id
        """

        where_clauses = []
        values = []

        # Filter by voucher_type
        if voucher_type:
            where_clauses.append("jv.voucher_type = %s")
            values.append(voucher_type.upper())

        # Filter by search (narration, listing_voucher, date)
        if search:
            where_clauses.append("""
                (jv.narration LIKE %s OR jv.listing_voucher LIKE %s OR DATE_FORMAT(jv.date, '%Y-%m-%d') LIKE %s)
            """)
            values.extend([f"%{search}%"] * 3)

        # Combine WHERE clauses
        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)

        # ---------------- Count Total Records ---------------- #
        count_query = f"SELECT COUNT(DISTINCT jv.id) AS total {base_query} {where_clause}"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()['total']

        # ---------------- Data Query with Pagination ---------------- #
        data_query = f"""
            SELECT 
                jv.id,
                jv.date,
                jv.narration,
                jv.voucher_type,
                jv.listing_voucher,
                COUNT(jve.id) AS total_entries
            {base_query}
            {where_clause}
            GROUP BY jv.id
            ORDER BY jv.id DESC
            LIMIT %s OFFSET %s
        """
        values.extend([record_per_page, offset])
        cursor.execute(data_query, values)
        vouchers = cursor.fetchall()
        cursor.close()

        # ---------------- Pagination Calculation ---------------- #
        total_pages = math.ceil(total_records / record_per_page)
        execution_time = time.time() - start_time

        return jsonify({
            "data": vouchers,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": execution_time
        }), 200

    except Exception as e:
        execution_time = time.time() - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500


# -------------------- UPDATE (PUT) -------------------- #
@voucher_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_journal_voucher(id):
    start_time = time.time()
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
        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            end_time = time.time()
            execution_time = end_time - start_time
            return jsonify({"message": "Journal Voucher not found", "execution_time": execution_time}), 404

        cursor.execute("""
            UPDATE journal_voucher
            SET date = %s, narration = %s, voucher_type = %s
            WHERE id = %s
        """, (date, narration, voucher_type.upper(), id))

        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))

        for entry in entries:
            account_head_id = entry.get('account_head_id')
            dr = entry.get('dr', 0)
            cr = entry.get('cr', 0)

            if not account_head_id:
                end_time = time.time()
                execution_time = end_time - start_time
                return jsonify({"error": "Each entry must have account_head_id", "execution_time": execution_time}), 400

            cursor.execute("""
                INSERT INTO journal_voucher_entries
                (journal_voucher_id, account_head_id, dr, cr, type, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id, account_head_id, dr, cr, voucher_type.upper(), date))

        mysql.connection.commit()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({
            "message": "Journal Voucher updated successfully",
            "voucher_id": id,
            "voucher_type": voucher_type.upper(),
            "execution_time": execution_time
        }), 200

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500


# -------------------- DELETE -------------------- #
@voucher_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_journal_voucher(id):
    start_time = time.time()
    try:
        mysql = current_app.mysql  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM journal_voucher WHERE id = %s", (id,))
        voucher = cursor.fetchone()
        if not voucher:
            cursor.close()
            end_time = time.time()
            execution_time = end_time - start_time
            return jsonify({"message": "Journal Voucher not found", "execution_time": execution_time}), 404

        cursor.execute("DELETE FROM journal_voucher_entries WHERE journal_voucher_id = %s", (id,))
        cursor.execute("DELETE FROM journal_voucher WHERE id = %s", (id,))

        mysql.connection.commit()
        cursor.close()

        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"message": "Journal Voucher deleted successfully", "execution_time": execution_time}), 200

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"error": str(e), "execution_time": execution_time}), 500



# -------------------- GET ALL -------------------- 
@voucher_bp.route('/all', methods=['GET'])
@token_required
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

# -------------------- VOUCHER PRINT PDF API -------------------- #
@voucher_bp.route('/print_pdf/<int:id>', methods=['GET'])
@token_required
def print_voucher_pdf(id):
    """
    Fetch voucher and return as downloadable PDF.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from io import BytesIO
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

        # Step 2: Get voucher entries WITHOUT JOIN
        cursor.execute("""
            SELECT id, account_head_id, dr, cr
            FROM journal_voucher_entries
            WHERE journal_voucher_id = %s
        """, (id,))
        entries = cursor.fetchall()

        # Step 2a: Loop through each entry to get account head name
        for e in entries:
            cursor.execute("SELECT name_head FROM account_heads WHERE id=%s", (e['account_head_id'],))
            account = cursor.fetchone()
            e['account_head_name'] = account['name_head'] if account else "Unknown"

        cursor.close()

        # Step 3: Prepare PDF
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        y = 750  # Starting height

        # ---------- PDF HEADER with LOGO ----------
        logo_path = os.path.join(current_app.root_path, "static", "uploads", "logo.jpg")
        logo_path = os.path.abspath(logo_path)  
        logo_path = logo_path.replace("\\", "/") 
        logo_width = 100
        logo_height = 50
        logo_x = 50
        logo_y = y - logo_height + 10  # Adjust vertical alignment with text

        # Draw logo
        pdf.drawImage(logo_path, logo_x, logo_y, width=100, height=50, mask='auto')
        # pdf.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')

        # Draw Voucher text (aligned center relative to page)
        pdf.setFont("Helvetica-Bold", 18)
        text_x = width / 2
        pdf.drawCentredString(text_x, y, "VOUCHER PRINT")
        y -= 80  # Move down after header

        # ---------- Voucher Info ----------
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, y, f"Voucher ID: {voucher['id']}")
        y -= 20
        pdf.drawString(50, y, f"Type: {voucher['voucher_type']}")
        y -= 20
        pdf.drawString(50, y, f"Date: {voucher['date']}")
        y -= 20
        pdf.drawString(50, y, f"Listing Voucher: {voucher['listing_voucher']}")
        y -= 20
        pdf.drawString(50, y, f"Narration: {voucher['narration']}")
        y -= 30

        # ---------- Entries Table Header ----------
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Account Head")
        pdf.drawRightString(330, y, "Debit")
        pdf.drawRightString(430, y, "Credit")
        y -= 20
        pdf.line(50, y, 500, y)
        y -= 20

        total_dr = 0
        total_cr = 0

        # ---------- Entries in Table ----------
        pdf.setFont("Helvetica", 11)
        for e in entries:
            account_head = str(e["account_head_name"])
            debit = float(e["dr"])
            credit = float(e["cr"])

            pdf.drawString(50, y, account_head)
            pdf.drawRightString(330, y, f"{debit:,.2f}")
            pdf.drawRightString(430, y, f"{credit:,.2f}")

            total_dr += debit
            total_cr += credit

            y -= 20

            # New page if needed
            if y < 50:
                pdf.showPage()
                y = 750

        # ---------- Totals ----------
        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(330, y, f"{total_dr:,.2f}")
        pdf.drawRightString(430, y, f"{total_cr:,.2f}")
        y -= 20
        pdf.drawString(50, y, "TOTALS")

        # Save PDF
        pdf.save()

        buffer.seek(0)

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=voucher_{id}.pdf'

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voucher_bp.route('/ledger', methods=['GET'])
@token_required
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
