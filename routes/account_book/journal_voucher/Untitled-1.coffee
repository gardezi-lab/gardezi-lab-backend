@voucher_bp.route('/ledger', methods=['GET'])
def get_ledger_report():
   
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get parameters from request
        account_head_id = request.args.get('account_head_id', type=int)
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        # Validate inputs
        if not account_head_id or not from_date or not to_date:
            return jsonify({"error": "account_head_id, from_date, and to_date are required"}), 400

        # Fetch account head name
        cursor.execute("SELECT name_head FROM account_heads WHERE id = %s", (account_head_id,))
        head = cursor.fetchone()
        if not head:
            cursor.close()
            return jsonify({"error": "Invalid account_head_id"}), 404

        # Fetch ledger entries
        cursor.execute("""
            SELECT 
                jv.date,
                jv.voucher_type,
                jv.listing_voucher,
                jv.narration,
                jve.dr,
                jve.cr
            FROM journal_voucher_entries AS jve
            LEFT JOIN journal_voucher AS jv
                ON jve.journal_voucher_id = jv.id
            WHERE jve.account_head_id = %s
              AND jv.date BETWEEN %s AND %s
            ORDER BY jv.date ASC, jv.id ASC
        """, (account_head_id, from_date, to_date))

        entries = cursor.fetchall()

        # Calculate totals
        total_dr = sum(float(e["dr"] or 0) for e in entries)
        total_cr = sum(float(e["cr"] or 0) for e in entries)

        cursor.close()

        # Return JSON response
        return jsonify({
            "message": "Ledger fetched successfully",
            "account_head_id": account_head_id,
            "account_head_name": head["name_head"],
            "from_date": from_date,
            "to_date": to_date,
            "total_dr": total_dr,
            "total_cr": total_cr,
            "entries": entries
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
