
import math
from flask import Blueprint, request, jsonify,current_app
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
import MySQLdb

results_bp = Blueprint('results', __name__, url_prefix='/api/results')
mysql = MySQL()

# -------------------- Create a new result -------------------- #
@results_bp.route('/', methods=['POST'])
def create_result():
    try:
        data = request.get_json()

        # --- Basic result info ---
        name = data.get("name")
        mr = data.get("mr")
        patient_id = data.get("patient_id")
        date = data.get("date") or datetime.now().strftime('%Y-%m-%d')
        add_results = data.get("add_results", "")
        sample = data.get("sample")
        tests = data.get("tests", [])  # list of tests with parameters

        # --- Validations ---
        if not name or not name.strip():
            return jsonify({"error": "Name is required"}), 400
        if not mr or not mr.strip():
            return jsonify({"error": "MR is required"}), 400
        if not patient_id:
            return jsonify({"error": "Patient ID is required"}), 400
        if not sample or not sample.strip():
            return jsonify({"error": "Sample is required"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        # --- Insert into results table ---
        cursor.execute(
            "INSERT INTO results (name, mr, date, add_results, sample, patient_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, mr, date, add_results, sample, patient_id)
        )
        result_id = cursor.lastrowid

        # --- Insert parameter results ---
        for test in tests:
            patient_test_id = test.get("patient_test_id")
            parameters = test.get("parameters", [])

            for param in parameters:
                parameter_id = param.get("id")
                # Use provided result_value, fallback to default_value
                result_value = param.get("result_value") or param.get("default_value", "")

                if patient_test_id and parameter_id:
                    cursor.execute(
                        """
                        INSERT INTO patient_results (patient_test_id, parameter_id, result_value)
                        VALUES (%s, %s, %s)
                        """,
                        (patient_test_id, parameter_id, result_value)
                    )

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Result added successfully",
            "result_id": result_id,
            "name": name,
            "mr": mr,
            "patient_id": patient_id,
            "date": date,
            "add_results": add_results,
            "sample": sample
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#---------------------Get patient test result by patient id ----------------------

from MySQLdb.cursors import DictCursor

@results_bp.route('/patient/<int:patient_id>', methods=['GET'])
def get_patient_results(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        query = """
        SELECT 
            r.id AS result_id,
            r.name,
            r.mr,
            r.date,
            r.add_results,
            r.sample,
            pt.id AS patient_test_id,
            tp.test_name,
            pr.parameter_id,
            p.parameter_name,
            p.unit,
            p.normalvalue,
            pr.result_value
        FROM results r
        JOIN patient_entry pe ON r.patient_id = pe.id
        JOIN patient_tests pt ON pt.patient_id = pe.id
        JOIN test_profiles tp ON tp.id = pt.test_id
        LEFT JOIN patient_results pr ON pr.patient_test_id = pt.id
        LEFT JOIN parameters p ON p.id = pr.parameter_id
        WHERE r.patient_id = %s
        ORDER BY r.date DESC, pt.id, p.id
        """
        cursor.execute(query, (patient_id,))
        rows = cursor.fetchall()
        cursor.close()

        # --- Transform rows to structured JSON ---
        results_dict = {}
        for row in rows:
            result_id = row['result_id']
            if result_id not in results_dict:
                results_dict[result_id] = {
                    "result_id": result_id,
                    "patient_id": patient_id,
                    "name": row['name'],
                    "mr": row['mr'],
                    "date": str(row['date']),
                    "add_results": row['add_results'],
                    "sample": row['sample'],
                    "tests": {}
                }

            test_id = row['patient_test_id']
            if test_id and test_id not in results_dict[result_id]['tests']:
                results_dict[result_id]['tests'][test_id] = {
                    "test_name": row['test_name'],
                    "parameters": []
                }

            if row['parameter_id']:
                results_dict[result_id]['tests'][test_id]['parameters'].append({
                    "parameter_id": row['parameter_id'],
                    "parameter_name": row['parameter_name'],
                    "unit": row['unit'],
                    "normalvalue": row['normalvalue'],
                    "result_value": row['result_value']
                })

        # Convert tests dict to list
        final_results = []
        for r in results_dict.values():
            r['tests'] = list(r['tests'].values())
            final_results.append(r)

        return jsonify(final_results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Get all results (with search + pagination) -------------------- #
@results_bp.route('/', methods=['GET'])
def get_results():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # Base query
        base_query = "SELECT * FROM results"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("(name LIKE %s OR mr LIKE %s OR sample LIKE %s OR add_results LIKE %s)")
            values.extend([f"%{search}%"] * 4)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        results = cursor.fetchall()
        cursor.close()

        formatted_results = [
            {
                "id": r["id"],
                "name": r["name"],
                "mr": r["mr"],
                "date": r["date"].strftime("%Y-%m-%d") if r["date"] else None,
                "add_results": r["add_results"],
                "sample": r["sample"]
            }
            for r in results
        ]

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": formatted_results,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Get result by ID -------------------- #
@results_bp.route('/<int:result_id>', methods=['GET'])
def get_result_by_id(result_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return jsonify({"error": "Result not found"}), 404

        if row["date"]:
            row["date"] = row["date"].strftime("%Y-%m-%d")

        return jsonify(row), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Update result -------------------- #
@results_bp.route('/<int:result_id>', methods=['PUT'])
def update_result(result_id):
    try:
        data = request.get_json()
        name = data.get("name")
        mr = data.get("mr")
        date = data.get("date")
        add_results = data.get("add_results")
        sample = data.get("sample")

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"error": "Result not found"}), 404

        update_query = """
            UPDATE results
            SET name=%s, mr=%s, date=%s, add_results=%s, sample=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (name, mr, date, add_results, sample, result_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Result updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- Delete result -------------------- #
@results_bp.route('/<int:result_id>', methods=['DELETE'])
def delete_result(result_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM results WHERE id = %s", (result_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"error": "Result not found"}), 404

        cursor.execute("DELETE FROM results WHERE id = %s", (result_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Result deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# -------------------- Get only pending results (no add_results) -------------------- #
@results_bp.route('/pending', methods=['GET'])
def get_pending_results():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Optional search & pagination
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        base_query = "SELECT * FROM results WHERE (add_results IS NULL OR add_results = '')"
        values = []

        if search:
            base_query += " AND (name LIKE %s OR mr LIKE %s OR sample LIKE %s)"
            values.extend([f"%{search}%"] * 3)

        # Count total pending
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # Apply pagination
        base_query += " LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])

        cursor.execute(base_query, values)
        pending_results = cursor.fetchall()
        cursor.close()

        formatted = [
            {
                "id": r["id"],
                "name": r["name"],
                "mr": r["mr"],
                "date": r["date"].strftime("%Y-%m-%d") if r["date"] else None,
                "add_results": r["add_results"],
                "sample": r["sample"]
            }
            for r in pending_results
        ]

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": formatted,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#----------------------- Add parameter rseult by test_profile_id - -----
@results_bp.route('/add-parameters', methods=['POST'])
def add_parameter_results():
    try:
        data = request.get_json()

        patient_test_id = data.get("patient_test_id")
        patient_id = data.get("patient_id")
        test_profile_id = data.get("test_profile_id")
        parameters = data.get("parameters", [])

        if not patient_test_id:
            return jsonify({"error": "Field 'patient_test_id' is required"}), 400
        if not patient_id:
            return jsonify({"error": "Field 'patient_id' is required"}), 400
        if not test_profile_id:
            return jsonify({"error": "Field 'test_profile_id' is required"}), 400
        if not parameters or not isinstance(parameters, list):
            return jsonify({"error": "Field 'parameters' must be a non-empty list"}), 400

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # --- Insert parameter results ---
        insert_query = """
            INSERT INTO patient_results (patient_id, patient_test_id, test_profile_id, parameter_id, result_value, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """

        for param in parameters:
            parameter_id = param.get("parameter_id")
            result_value = param.get("result_value")

            if parameter_id is None or result_value is None:
                continue

            cursor.execute(insert_query, (patient_id, patient_test_id, test_profile_id, parameter_id, result_value))

        # --- Log activity for adding test results ---
        from datetime import datetime
        now_time = datetime.now()

        # Get last activity for turnaround_time
        cursor.execute("""
            SELECT created_at 
            FROM patient_activity_log
            WHERE patient_id = %s
            ORDER BY id DESC LIMIT 1
        """, (patient_id,))
        last_record = cursor.fetchone()

        if last_record and last_record['created_at']:
            reference_time = last_record['created_at']
        else:
            # First activity → use patient_entry created_at
            cursor.execute("""
                SELECT created_at
                FROM patient_entry
                WHERE id = %s
                LIMIT 1
            """, (patient_id,))
            entry_record = cursor.fetchone()
            reference_time = entry_record['created_at'] if entry_record and entry_record['created_at'] else now_time

        turnaround_time = str(now_time - reference_time)

        # Insert activity log
        cursor.execute("""
            INSERT INTO patient_activity_log (patient_id, activity,  created_at)
            VALUES (%s, %s, %s)
        """, (patient_id, "Test Results Added", now_time))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Parameter results added successfully",
            "patient_id": patient_id,
            "patient_test_id": patient_test_id,
            "test_profile_id": test_profile_id,
            "total_parameters_added": len(parameters),
            "activity": "Test Results Added",
            "turnaround_time": turnaround_time
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-------------- GET patient all test their result add or not -----------
@results_bp.route('/patient_results/<int:patient_id>', methods=['GET'])
def get_patient_tests_with_results(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #  Patient ke selected tests
        cursor.execute("""
            SELECT pt.id AS patient_test_id,
                   tp.id AS test_profile_id,
                   tp.test_name
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_profile_id = tp.id
            WHERE pt.patient_id = %s
        """, (patient_id,))
        patient_tests = cursor.fetchall()

        response = []

        for test in patient_tests:
            patient_test_id = test['patient_test_id']
            test_profile_id = test['test_profile_id']

            #  Parameters + unka result (LEFT JOIN)
            cursor.execute("""
                SELECT p.id AS parameter_id,
                       p.parameter_name,
                       p.unit,
                       p.normalvalue,
                       p.default_value,
                       pr.result_value
                FROM parameters p
                LEFT JOIN patient_results pr
                    ON pr.parameter_id = p.id
                    AND pr.patient_test_id = %s
                    AND pr.test_profile_id = %s
                WHERE p.test_profile_id = %s
            """, (patient_test_id, test_profile_id, test_profile_id))

            parameters = cursor.fetchall()

            response.append({
                "patient_test_id": patient_test_id,
                "test_profile_id": test_profile_id,
                "test_name": test['test_name'],
                "parameters": parameters
            })

        cursor.close()

        return jsonify({
            "patient_id": patient_id,
            "tests": response
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
