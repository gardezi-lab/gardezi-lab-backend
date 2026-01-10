from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
import MySQLdb
from flask_mysqldb import MySQL
import time
from routes.authentication.authentication import token_required


reporting_bp = Blueprint('reporting', __name__, url_prefix='/api/reporting')
mysql = MySQL()


# ------------------ TODO Reception report --get all data their role is receptionist by their id and  from date to date -----------------------
@reporting_bp.route('/receptionists_report/<int:center_id>', methods=['GET'])
@token_required
def get_receptionists_by_date(center_id):
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 30, type=int)
        offset = (current_page - 1) * record_per_page

        if not from_date or not to_date:
            return jsonify({
                "data": [],
                "count": 0,
                "execution_time": time.time() - start_time
            }), 200

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 🔹 Base query
        query = """
            SELECT 
                u.id AS receptionist_id,
                u.name AS receptionist_name,
                u.contact_no,
                r.name AS ref_name,
                u.role,
                DATE(u.created_at) AS created_date,
                p.age,
                p.patient_name AS patient_name,
                p.mr_number,
                c.total_fee,
                c.paid,
                (c.total_fee - c.paid) AS due,
                GROUP_CONCAT(tp.test_name) AS tests,
                c.created_at AS patient_entry_date
            FROM users u
            LEFT JOIN counter c ON c.user_id = u.id
            LEFT JOIN patient_entry p ON p.id = c.pt_id
            LEFT JOIN patient_tests t ON t.counter_id = c.id
            LEFT JOIN test_profiles tp ON tp.id = t.test_id
            LEFT JOIN users r ON r.id = c.reff_by
            WHERE u.role = 'Reception' AND u.id = %s
            AND c.created_at BETWEEN %s AND %s
            GROUP BY c.id
            ORDER BY u.id DESC, c.id DESC
            LIMIT %s OFFSET %s
        """
        params = [center_id, from_date, to_date, record_per_page, offset]

        cursor.execute(query, params)
        results = cursor.fetchall()

        # 🔹 total count (without pagination) for frontend info
        count_query = """
            SELECT COUNT(DISTINCT c.id) AS total
            FROM users u
            LEFT JOIN counter c ON c.user_id = u.id
            WHERE u.role = 'Reception' AND u.id = %s
            AND c.created_at BETWEEN %s AND %s
        """
        cursor.execute(count_query, [center_id, from_date, to_date])
        total_records = cursor.fetchone()['total']

        end_time = time.time()

        return jsonify({
            "data": results,
            "totalrecords": total_records,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()



# ----------------TODO doctor report --get all data their role is doctor with from date sy to date------------------------
@reporting_bp.route('/doctors_report/<int:doctor_id>', methods=['GET'])
@token_required
def get_doctors_by_date(doctor_id):
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 30, type=int)
        offset = (current_page - 1) * record_per_page

        if not from_date or not to_date:
            return jsonify({
                "doctor_id": doctor_id,
                "doctor_name": None,
                "patients": [],
                "execution_time": time.time() - start_time
            }), 200

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 🔹 Base query
        query = """
        SELECT 
            u.id AS doctor_id,
            u.name AS doctor_name,
            p.patient_name,
            p.mr_number,
            c.total_fee,
            c.paid,
            (c.total_fee - c.paid) AS due,
            GROUP_CONCAT(DISTINCT tp.test_name ORDER BY tp.test_name ASC) AS tests,
            MAX(t.verified_at) AS verified_date
        FROM users u
        LEFT JOIN patient_tests t ON t.verified_by = u.id
        LEFT JOIN counter c ON c.id = t.counter_id
        LEFT JOIN patient_entry p ON p.id = c.pt_id
        LEFT JOIN test_profiles tp ON tp.id = t.test_id
        WHERE u.role = 'Doctor' AND u.id = %s
          AND DATE(t.verified_at) BETWEEN %s AND %s
        GROUP BY t.counter_id
        ORDER BY MAX(t.verified_at) DESC
        LIMIT %s OFFSET %s
        """
        params = [doctor_id, from_date, to_date, record_per_page, offset]

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Format output per doctor
        doctor_data = {}
        patients = []

        for row in rows:
            tests_list = row['tests'].split(',') if row.get('tests') else []
            verified_date = row['verified_date'].strftime('%Y-%m-%d %H:%M:%S') if row.get('verified_date') else None

            patients.append({
                "patient_name": row.get('patient_name'),
                "mr_number": row.get('mr_number'),
                "total_fee": row.get('total_fee'),
                "paid": row.get('paid'),
                "due": row.get('due'),
                "tests": tests_list,
                "verified_date": verified_date
            })

            doctor_data = {
                "doctor_id": row.get('doctor_id'),
                "doctor_name": row.get('doctor_name'),
                "patients": patients
            }

        # 🔹 Total patients count (without pagination)
        count_query = """
        SELECT COUNT(DISTINCT t.counter_id) AS total
        FROM users u
        LEFT JOIN patient_tests t ON t.verified_by = u.id
        LEFT JOIN counter c ON c.id = t.counter_id
        WHERE u.role = 'Doctor' AND u.id = %s
          AND DATE(t.verified_at) BETWEEN %s AND %s
        """
        cursor.execute(count_query, [doctor_id, from_date, to_date])
        total_records = cursor.fetchone()['total']

        end_time = time.time()
        doctor_data['execution_time'] = end_time - start_time
        doctor_data['total_records'] = total_records  # optional if future use

        return jsonify(doctor_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()



# ---------------------- TODO LAB report -- get all users their role is reception and cc is equel to given id -----------------------
@reporting_bp.route('/cc_report/<int:cc_id>', methods=['GET'])
@token_required
def get_receptionists_by_cc(cc_id):
    start_time = time.time()
    cursor = None
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 🔹 Date Filters
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        # 🔹 Pagination params
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 30, type=int)
        offset = (current_page - 1) * record_per_page

        # Step 1: Get Receptionists
        cursor.execute("""
            SELECT id, name
            FROM users 
            WHERE role = 'Reception' AND cc = %s
        """, (cc_id,))
        receptionists = cursor.fetchall()

        if not receptionists:
            return jsonify({
                "count": 0,
                "data": [],
                "execution_time": time.time() - start_time
            }), 200

        receptionist_ids = [r['id'] for r in receptionists]
        format_strings = ','.join(['%s'] * len(receptionist_ids))

        date_condition = ""
        params = list(receptionist_ids)

        if from_date and to_date:
            date_condition = " AND c.date_created BETWEEN %s AND %s "
            params.append(from_date)
            params.append(to_date)

        # Step 2: Main query with pagination
        query = f"""
            SELECT 
                pe.patient_name,
                pe.age,
                pe.cell AS contact_no,
                pe.created_at AS patient_entry_date,
                pe.mr_number,
                c.total_fee,
                c.paid,
                (c.total_fee - c.paid) AS due,
                c.date_created AS created_date,
                u2.id AS receptionist_id,
                u2.name AS receptionist_name,
                u2.role,
                u.name AS ref_name,
                GROUP_CONCAT(tp.test_name SEPARATOR ', ') AS tests
            FROM patient_entry pe
            LEFT JOIN counter c ON pe.id = c.pt_id
            LEFT JOIN users u ON c.reff_by = u.id
            LEFT JOIN users u2 ON pe.user_id = u2.id
            LEFT JOIN patient_tests pt ON pe.id = pt.patient_id
            LEFT JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pe.user_id IN ({format_strings})
            {date_condition}
            GROUP BY 
                pe.id, 
                pe.patient_name, 
                pe.age, 
                pe.cell,
                pe.created_at,
                pe.mr_number,
                c.total_fee,
                c.paid,
                c.date_created,
                u2.id,
                u2.name,
                u2.role,
                u.name
            ORDER BY pe.id DESC
            LIMIT %s OFFSET %s
        """
        params.extend([record_per_page, offset])

        cursor.execute(query, tuple(params))
        data = cursor.fetchall()

        # 🔹 Total count without pagination
        count_query = f"""
            SELECT COUNT(DISTINCT pe.id) AS total
            FROM patient_entry pe
            LEFT JOIN counter c ON pe.id = c.pt_id
            WHERE pe.user_id IN ({format_strings})
        """
        count_params = list(receptionist_ids)
        if from_date and to_date:
            count_query += " AND c.date_created BETWEEN %s AND %s"
            count_params.extend([from_date, to_date])

        cursor.execute(count_query, tuple(count_params))
        total_records = cursor.fetchone()['total']

        cursor.close()
        end_time = time.time()

        return jsonify({
            "count": total_records,
            "data": data,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()

# ----------------------- TODO Technician report -----------------------
@reporting_bp.route('/technician_report/<int:technician_id>', methods=['GET'])
@token_required
def technician_report(technician_id):
    start_time = time.time()
    cursor = None
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        current_page = request.args.get('currentpage', 1, type=int)
        record_per_page = request.args.get('recordperpage', 30, type=int)
        offset = (current_page - 1) * record_per_page

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 🔹 Base query
        query = """
            SELECT 
                u.name AS technician_name,
                tp.test_name,
                p.patient_name,
                p.mr_number,
                DATE(t.created_at) AS date
            FROM users u
            LEFT JOIN patient_tests t ON t.performed_by = u.id
            LEFT JOIN counter c ON c.id = t.counter_id
            LEFT JOIN patient_entry p ON p.id = c.pt_id
            LEFT JOIN test_profiles tp ON tp.id = t.test_id
            WHERE u.role = 'Technician' AND u.id = %s
        """
        params = [technician_id]

        # 🔹 Optional date filter
        if from_date and to_date:
            query += " AND DATE(t.created_at) BETWEEN %s AND %s"
            params.extend([from_date, to_date])

        # 🔹 Total count (without pagination)
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM patient_tests t
            LEFT JOIN users u ON t.performed_by = u.id
            WHERE u.role = 'Technician' AND u.id = %s
        """
        count_params = [technician_id]
        if from_date and to_date:
            count_query += " AND DATE(t.created_at) BETWEEN %s AND %s"
            count_params.extend([from_date, to_date])
        cursor.execute(count_query, count_params)
        total_records = cursor.fetchone()['total']

        # 🔹 Pagination
        query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
        params.extend([record_per_page, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        end_time = time.time()

        return jsonify({
            "technician_id": technician_id,
            "technician_name": rows[0]['technician_name'] if rows else None,
            "tests": rows,
            "execution_time": end_time - start_time,
            "total_records": total_records  # optional for frontend
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()

# ----------------------- TODO business report -----------------------    
@reporting_bp.route('/business_report', methods=['GET'])
@token_required
def get_business_reports():
    start_time = time.time()
    cursor = None
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Default conditions (match everything)
        counter_date_filter = " WHERE 1=1 "
        tests_date_filter = " WHERE 1=1 "
        params = ()

        if start_date and end_date:
            # keep original logic (dates injected directly into the subquery strings)
            counter_date_filter = f" WHERE date_created BETWEEN '{start_date}' AND '{end_date}' "
            tests_date_filter = f" WHERE verified_at BETWEEN '{start_date}' AND '{end_date}' "

        query = f"""
        SELECT
            -- Patient Details (from 'counter' table)
            (SELECT COUNT(*) FROM counter {counter_date_filter}) AS total_patient,
            (SELECT COUNT(*) FROM counter {counter_date_filter} AND status = 0) AS pending_patient,
            (SELECT COUNT(*) FROM counter {counter_date_filter} AND status = 1) AS patient_processed,

            -- Amount Summary (from 'counter' table)
            (SELECT SUM(discount) FROM counter {counter_date_filter} AND discount > 0) AS total_discount,
            (SELECT SUM(total_fee) FROM counter {counter_date_filter}) AS total_amount,
            (SELECT SUM(paid) FROM counter {counter_date_filter}) AS paid_amount,
            (SELECT SUM(total_fee - paid) FROM counter {counter_date_filter}) AS due_amount,

            -- Test Details (from 'patient_tests' table)
            (SELECT COUNT(*) FROM patient_tests {tests_date_filter}) AS total_test,
            (SELECT COUNT(*) FROM patient_tests {tests_date_filter} AND status = 1) AS processed_test,
            (SELECT COUNT(*) FROM patient_tests {tests_date_filter} AND status = 0) AS unprocessed_test_count
        """

        cursor.execute(query, params)
        report = cursor.fetchone()

        if report is None:
            # ensure numeric zeros when no rows
            report = {"total_patient": 0, "pending_patient": 0, "patient_processed": 0,
                    "total_discount": 0, "total_amount": 0, "paid_amount": 0, "due_amount": 0,
                    "total_test": 0, "processed_test": 0, "unprocessed_test_count": 0}
        else:
            # replace None with 0 for keys present
            for k, v in report.items():
                if v is None:
                    report[k] = 0

        end_time = time.time()

        final_response = {
            "business_report": [
                {
                    "amount_summary": {
                        "due_amount": report["due_amount"],
                        "paid_amount": report["paid_amount"],
                        "total_amount": report["total_amount"],
                        "total_discount": report["total_discount"]
                    },
                    "tests_details": {
                        "total_test": report["total_test"],
                        "processed_test": report["processed_test"],
                        "unprocessed_test_count": report["unprocessed_test_count"]
                    },
                    "patient_details": {
                        "total_patient": report["total_patient"],
                        "pending_patient": report["pending_patient"],
                        "patient_processed": report["patient_processed"]
                    },
                    "execution_time": end_time - start_time
                }
            ]
        }

        return jsonify(final_response), 200

    except MySQLdb.Error as e:
        current_app.logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()
# ----------------------- TODO discount report ------------------------- 
@reporting_bp.route('/discount_report', methods=['GET'])
@token_required
def discount_report():
    start_time = time.time()

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    current_page = request.args.get('currentpage', 1, type=int)
    record_per_page = request.args.get('recordperpage', 30, type=int)
    offset = (current_page - 1) * record_per_page

    query = "SELECT * FROM counter WHERE discount > 0"
    params = []

    if from_date and to_date:
        query += " AND DATE(created_at) BETWEEN %s AND %s"
        params.extend([from_date, to_date])
    elif from_date:
        query += " AND DATE(created_at) >= %s"
        params.append(from_date)
    elif to_date:
        query += " AND DATE(created_at) <= %s"
        params.append(to_date)

    mysql = current_app.mysql
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Total count (without pagination)
    count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS subquery"
    cursor.execute(count_query, tuple(params))
    total_records = cursor.fetchone()['total']

    # 🔹 Pagination
    paginated_query = query + " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([record_per_page, offset])
    cursor.execute(paginated_query, tuple(params))
    data = cursor.fetchall()

    cursor.close()
    end_time = time.time()

    return jsonify({
        "data": data,
        "status": 200,
        "execution_time": end_time - start_time,
        "total_records": total_records  # optional for frontend
    })

#------------------TODO due report-------
@reporting_bp.route('/due_report', methods=['GET'])
@token_required
def simple_patient_list():
    start_time = time.time()

    current_page = request.args.get('currentpage', 1, type=int)
    record_per_page = request.args.get('recordperpage', 30, type=int)
    offset = (current_page - 1) * record_per_page

    mysql = current_app.mysql
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Step 1: Total due records count (without pagination)
    count_query = "SELECT COUNT(*) AS total FROM counter WHERE paid < total_fee"
    cursor.execute(count_query)
    total_records = cursor.fetchone()['total']

    # Step 2: Fetch due counter records with pagination
    query = "SELECT * FROM counter WHERE paid < total_fee ORDER BY id DESC LIMIT %s OFFSET %s"
    cursor.execute(query, (record_per_page, offset))
    counter_data = cursor.fetchall()

    final_data = []

    # Step 3: For each counter record, fetch patient details
    for row in counter_data:
        pt_id = row.get("pt_id")
        cursor.execute(
            "SELECT patient_name, mr_number FROM patient_entry WHERE id = %s",
            (pt_id,)
        )
        patient = cursor.fetchone()

        # Response build
        final_data.append({
            "id": row.get("id"),
            "pt_id": pt_id,
            "name": patient["patient_name"] if patient else "",
            "mr_number": patient["mr_number"] if patient else "",
            "total_fee": row.get("total_fee"),
            "paid": row.get("paid"),
            "due_amount": row.get("total_fee") - row.get("paid"),
        })

    cursor.close()
    end_time = time.time()

    return jsonify({
        "data": final_data,
        "status": 200,
        "execution_time": end_time - start_time,
        "total_records": total_records  # optional for frontend
    })


#-------------------  TODO log report ------------
@reporting_bp.route("/log_report/", methods=["GET"])
@token_required
def get_activity():
    start_time = time.time()

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM patient_activity_log ORDER BY created_at DESC")
        activities = cursor.fetchall()
        #activities mn patient id a raha os patient ka name get krna hay 
        for activity in activities:
            patient_id = activity['patient_id']
            cursor.execute("SELECT patient_name, mr_number FROM patient_entry WHERE id = %s", (patient_id,))
            patient = cursor.fetchone()
            if patient:
                activity['patient_name'] = patient['patient_name']
                activity['mr_number'] = patient['mr_number']
            else:
                activity['patient_name'] = None
                activity['mr_number'] = None
            
        cursor.close()
        end_time = time.time()

        return jsonify({"activities": activities, "status": 200,"execution_time": end_time - start_time
})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------------Sale report --------------
@reporting_bp.route('/sales_statement_report', methods=['GET'])
@token_required
def get_sales_report():
    start_time = time.time()

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not from_date or not to_date:
        return jsonify({
            "error": "Both 'from_date' and 'to_date' are required (YYYY-MM-DD)"
        }), 400

    mysql = current_app.mysql
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT 
            DATE(c.created_at) AS sale_date,
            c.total_fee,
            c.discount,
            c.total_fee - paid AS payment_recoveries,
            cc.id AS cc,
            cc.name AS collection_center_name,
            SUM(c.paid) AS payment_received
        FROM counter c
        LEFT JOIN collectioncenter cc 
            ON c.cc = cc.id
        WHERE DATE(c.created_at) BETWEEN %s AND %s
          AND c.trash = 0
        GROUP BY DATE(c.created_at), cc.id, cc.name
        ORDER BY sale_date ASC
    """

    cursor.execute(query, (from_date, to_date))
    data = cursor.fetchall()
    cursor.close()

    end_time = time.time()

    return jsonify({
        "data": data,
        "status": 200,
        "execution_time": end_time - start_time
    }), 200
