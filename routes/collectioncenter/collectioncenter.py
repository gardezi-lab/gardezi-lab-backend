from flask import Blueprint, request, jsonify,current_app
from flask_mysqldb import MySQL
from routes.authentication.authentication import token_required
from MySQLdb.cursors import DictCursor
import MySQLdb
import time
import math

collectioncenter_bp = Blueprint('collectioncenter', __name__, url_prefix='/api/collectioncenter')

# -------------------- Get all collection centers --------------------
@collectioncenter_bp.route('/', methods=['GET'])
@token_required
def get_collection_centers():
    start_time = time.time()
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 🔹 Query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # 🔹 Base query
        base_query = "SELECT * FROM collectioncenter"
        where_clauses = []
        params = []

        # 🔹 Filter (search)
        if search:
            where_clauses.append(
                "(name LIKE %s)"
            )
            params.extend([f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # 🔹 Count total records
        count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS subquery"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()["total"]

        # 🔹 Pagination + order
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([record_per_page, offset])

        cursor.execute(base_query, params)
        collection_centers = cursor.fetchall()

        end_time = time.time()
        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": collection_centers,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "executionTime": end_time - start_time
        }), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()


# ----------------------------------Add collection center-----------------------------
@collectioncenter_bp.route('/', methods=['POST'])
@token_required
def add_collection_center():
    start_time = time.time()
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    location = data.get('location')
    
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO collectioncenter (name, email, password, location) VALUES (%s, %s, %s, %s)",
            (name, email, password, location)
        )
        mysql.connection.commit()
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"message": "Collection center added successfully", "execution_time": execution_time}), 201
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------Update collection center-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['PUT'])
@token_required
def update_collection_center(center_id):
    start_time = time.time()
    
    data = request.get_json()
    name = data.get('name') 
    email = data.get('email')
    password = data.get('password')
    location = data.get('location')
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        cursor.execute(
            "UPDATE collectioncenter SET name=%s, email=%s, password=%s, location=%s WHERE id=%s",
            (name, email, password, location, center_id)
        )
        mysql.connection.commit()
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"message": "Collection center updated successfully", "execution_time": execution_time}), 200
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------Delete collection center-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['DELETE'])
@token_required
def delete_collection_center(center_id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        
        cursor.execute(
            "DELETE FROM collectioncenter WHERE id=%s",
            (center_id,)
        )
        mysql.connection.commit()
        end_time = time.time()
        execution_time = end_time - start_time
        return jsonify({"message": "Collection center deleted successfully", "execution_time": execution_time}), 200
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------GEt collection center by id-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['GET'])
@token_required
def get_collection_center(center_id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM collectioncenter WHERE id=%s",
            (center_id,)
        )
        collection_center = cursor.fetchone()
        end_time = time.time()
        execution_time = end_time - start_time
        if collection_center:
            collection_center['execution_time'] = execution_time
            return jsonify(collection_center), 200
        else:
            return jsonify({"error": "Collection center not found"}), 404
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ---------------------collection center report to collection center id and from date to to date-----------------------
# get these data patient_name, mr_number, test_name, total_fee, reff_by
@collectioncenter_bp.route('/report/<int:center_id>', methods=['GET'])
@token_required
def collection_center_report(center_id):
    start_time = time.time()
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not from_date or not to_date:
        from_date = "0001-01-01"
        to_date = "9999-12-31"

    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        query = """
            SELECT 
                pe.name AS patient_name,
                pe.mr_number,
                tp.test_name, 
                c.total_fee,
                u.name AS reff_by_name
            FROM collectioncenter cr
            LEFT JOIN patient_entry pe ON cr.patient_id = pe.id
            LEFT JOIN patient_tests pt ON cr.patient_id = pt.patient_id
            LEFT JOIN test_profiles tp ON pt.test_id = tp.id
            LEFT JOIN counter c ON cr.patient_id = c.patient_id
            LEFT JOIN users u ON pe.reff_by = u.id
            WHERE cr.id = %s 
            AND cr.report_date BETWEEN %s AND %s
        """

        cursor.execute(query, (center_id, from_date, to_date))
        reports = cursor.fetchall()

        end_time = time.time()
        execution_time = end_time - start_time

        return jsonify({
            "reports": reports,
            "execution_time": execution_time
        }), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()

