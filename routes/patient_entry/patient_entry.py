import math
from flask import Flask, request, jsonify, Blueprint, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL

patient_entry_bp = Blueprint('patient_entry', __name__, url_prefix='/api/patient_entry')
mysql = MySQL()

# ================== Patient Entry CRUD Operations ================== #

# ------------------- Create Patient Entry ------------------ #
@patient_entry_bp.route('/', methods=['POST'])
def create_patient_entry():
    try:
        data = request.get_json()
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test_string = data.get('test')  # e.g. "Complete Blood Count, LFT"

        if not all([cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test_string]):
            return jsonify({"error": "All fields are required"}), 400

        if not isinstance(age, int):
            return jsonify({"error": "age must be integer"}), 400

        # Split tests into list
        test_names = [t.strip() for t in test_string.split(",") if t.strip()]

        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        #  Calculate total fee from test_profiles
        format_strings = ','.join(['%s'] * len(test_names))
        cursor.execute(f"SELECT id, test_name, fee FROM test_profiles WHERE test_name IN ({format_strings})", test_names)
        test_rows = cursor.fetchall()

        total_fee = sum(int(row['fee']) for row in test_rows)

        #  Insert patient entry
        insert_query = """
            INSERT INTO patient_entry 
            (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test_string))
        patient_id = cursor.lastrowid

        #  Insert each test in patient_tests
        for row in test_rows:
            cursor.execute(
                "INSERT INTO patient_tests (patient_id, test_id) VALUES (%s, %s)",
                (patient_id, row['id'])
            )

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Patient entry created successfully",
            "patient_id": patient_id,
            "tests_added": [row['test_name'] for row in test_rows],
            "total_fee": total_fee
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- Patient Test GET -----------------------------------------
@patient_entry_bp.route('/<int:patient_id>/tests', methods=['GET'])
def get_patient_tests(patient_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        query = """
            SELECT t.test_name
            FROM patient_tests pt
            JOIN test_profiles t ON pt.test_id = t.id
            WHERE pt.patient_id = %s
        """
        cursor.execute(query, (patient_id,))
        results = cursor.fetchall()
        cursor.close()

        test_list = [row[0] for row in results]

        return jsonify({
            "patient_id": patient_id,
            "total_tests": len(test_list),
            "tests": test_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ------------------- Get All Patient Entries (Search + Pagination) ------------------ #
@patient_entry_bp.route('/', methods=['GET'])
def get_all_patient_entries():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # base query
        base_query = "SELECT * FROM patient_entry"
        where_clauses = []
        values = []

        if search:
            where_clauses.append(
                "(cell LIKE %s OR patient_name LIKE %s OR father_hasband_MR LIKE %s OR company LIKE %s OR reffered_by LIKE %s OR gender LIKE %s OR email LIKE %s OR address LIKE %s OR package LIKE %s OR sample LIKE %s OR priority LIKE %s OR remarks LIKE %s OR test LIKE %s)"
            )
            for _ in range(13):  # total searchable fields
                values.append(f"%{search}%")

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # count total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, values)
        total_records = cursor.fetchone()["total"]

        # pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cursor.execute(base_query, values)
        rows = cursor.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": rows,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

        return jsonify({
            "data" : paginate_query(cursor, base_query),
            "status" : 200})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Get Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['GET'])
def patient_get_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT * FROM patient_entry WHERE id = %s", (id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return jsonify({"patient_entry": row}), 200
            patient_entry = {
                "id": row[0],
                "cell": row[1],
                "patient_name": row[2],
                "father_hasband_MR": row[3],
                "age": row[4],
                "company": row[5],
                "reffered_by": row[6],
                "gender": row[7],
                "email": row[8],
                "address": row[9],
                "package": row[10],
                "sample": row[11],
                "priority": row[12],
                "remarks": row[13],
                "test": row[14],
                "status" : 200
            }
            return jsonify({"patient_entry": patient_entry}), 200
        return jsonify({"error": "Patient entry not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Update Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['PUT'])
def update_patient_entry(id):
    try:
        data = request.get_json()
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test = data.get('test')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        update_query = """
            UPDATE patient_entry
            SET cell=%s, patient_name=%s, father_hasband_MR=%s, age=%s, company=%s,
                reffered_by=%s, gender=%s, email=%s, address=%s, package=%s,
                sample=%s, priority=%s, remarks=%s, test=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test, id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry updated successfully",
                        "status": 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- Delete Patient Entry by ID ------------------ #
@patient_entry_bp.route('/<int:id>', methods=['DELETE'])
def delete_patient_entry(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM patient_entry WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry deleted successfully",
                        "status" : 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
