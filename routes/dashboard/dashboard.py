from flask import Blueprint, current_app, jsonify, request
import MySQLdb.cursors
import time
from routes.authentication.authentication import token_required


dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# ------------------TODO sales report ------------------
@dashboard_bp.route('/sale_report', methods=['GET'])
@token_required
def counter_report():
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 🔹 CASE 1: Date filter diya ho
        if from_date and to_date:
            query = """
                SELECT 
                    DATE(created_at) AS created_at,
                    SUM(total_fee) AS total_fee
                FROM counter
                WHERE DATE(created_at) BETWEEN %s AND %s
                GROUP BY DATE(created_at)
                ORDER BY created_at
            """
            params = (from_date, to_date)
        
        # 🔹 CASE 2: Default last 7 days
        else:
            query = """
                SELECT 
                    DATE(created_at) AS created_at,
                    SUM(total_fee) AS total_fee
                FROM counter
                WHERE DATE(created_at) >= CURDATE() - INTERVAL 7 DAY
                GROUP BY DATE(created_at)
                ORDER BY created_at
            """
            params = ()

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # 🔹 Convert total_fee to float
        for row in rows:
            row['total_fee'] = float(row['total_fee']) if row['total_fee'] is not None else 0

        end_time = time.time()

        return jsonify({
            "data": rows,
            "execution_time": round(end_time - start_time, 4)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()

# ------------------------TODO Reception Report ------------
@dashboard_bp.route('/cc_report', methods=['GET'])
@token_required
def cc_sale_report():
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 🔹 CASE 1: Date filter (date-wise per CC)
        if from_date and to_date:
            query = """
                SELECT 
                    c.cc AS cc_id,
                    cc.name AS cc_name,
                    DATE(c.created_at) AS report_date,
                    SUM(c.total_fee) AS total_sale
                FROM counter c
                JOIN collectioncenter cc ON cc.id = c.cc
                WHERE DATE(c.created_at) BETWEEN %s AND %s
                GROUP BY c.cc, DATE(c.created_at)
                ORDER BY c.cc, report_date
            """
            params = (from_date, to_date)

        # 🔹 CASE 2: Default last 7 days (total per CC)
        else:
            query = """
                SELECT 
                    c.cc AS cc_id,
                    cc.name AS cc_name,
                    SUM(c.total_fee) AS total_sale
                FROM counter c
                JOIN collectioncenter cc ON cc.id = c.cc
                WHERE DATE(c.created_at) >= CURDATE() - INTERVAL 7 DAY
                GROUP BY c.cc
                ORDER BY total_sale DESC
            """
            params = ()

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # 🔹 Convert total_sale to float
        for row in rows:
            row['total_sale'] = float(row['total_sale']) if row['total_sale'] is not None else 0

        end_time = time.time()

        return jsonify({
            "data": rows,
            "execution_time": round(end_time - start_time, 4)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()

# ---------------TODO technician report ----------
@dashboard_bp.route('/technician_report', methods=['GET'])
@token_required
def technician_report():
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if from_date and to_date:
            query = """
                SELECT 
                    u.id AS technician_id,
                    u.name AS technician_name,
                    DATE(pt.performed_date) AS report_date,
                    COUNT(pt.id) AS total_tests
                FROM patient_tests pt
                JOIN users u ON u.id = pt.performed_by
                WHERE pt.result_status = 1 
                AND pt.performed_date IS NOT NULL
                AND pt.performed_date >= %s
                AND pt.performed_date < DATE_ADD(%s, INTERVAL 1 DAY)
                GROUP BY u.id, DATE(pt.performed_date)
                ORDER BY report_date, technician_name
            """
            params = (from_date, to_date)

        else:
            query = """
                SELECT 
                    u.id AS technician_id,
                    u.name AS technician_name,
                    COUNT(pt.id) AS total_tests
                FROM patient_tests pt
                JOIN users u ON u.id = pt.performed_by
                WHERE pt.result_status = 1
                AND pt.performed_date >= CURDATE()
                AND pt.performed_date < CURDATE() + INTERVAL 1 DAY
                GROUP BY u.id
                ORDER BY total_tests DESC
            """
            params = ()

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return jsonify({
            "data": rows,
            "execution_time": round(time.time() - start_time, 4)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
# -------------------------TODO Expense Report ------------------
@dashboard_bp.route('/expense_report', methods=['GET'])
@token_required
def expense_report():
    start_time = time.time()  # start timer
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        if not from_date or not to_date:
            return jsonify({
                "status": "error",
                "message": "from_date and to_date are required"
            }), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        query = """
            SELECT
                j.date AS report_date,
                j.voucher_type,
                SUM(e.dr) AS total_expense
            FROM journal_voucher j
            JOIN journal_voucher_entries e 
                ON e.journal_voucher_id = j.id
            WHERE j.date BETWEEN %s AND %s
            AND j.voucher_type IN ('JV', 'CPV', 'BPV', 'BRV', 'CRV')
            GROUP BY j.date, j.voucher_type
            ORDER BY j.date, j.voucher_type
        """

        cursor.execute(query, (from_date, to_date))
        rows = cursor.fetchall()
        end_time = time.time()  #  end timer

        return jsonify({
            "data": rows,
            "execution_time": round(end_time - start_time, 4)  #  execution time in seconds
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()