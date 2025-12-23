import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor
import time
from routes.authentication.authentication import token_required

packages_bp = Blueprint('packages_bp', __name__, url_prefix='/api/test-packages')

# -------- Helper: Validation --------
def validate_package_data(data, is_update=False):
    if not is_update:  
        if not data.get("name"):
            return "name is required"
        if not data.get("price"):
            return "price is required"
        if not data.get("selected_test"):
            return "selected_test is required"

    if data.get("price"):
        try:
            float(data["price"])
        except ValueError:
            return "price must be numeric"

    return None  # valid


# -------- CREATE (POST) --------
@packages_bp.route('/', methods=['POST'])
@token_required
def create_package():
    start_time = time.time()
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_package_data(data, is_update=False)
    if error:
        return jsonify({"error": error}), 400
    selected_tests = data.get('selected_test', [])
    
    selected_tests = ','.join(str(t) for t in selected_tests)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO test_packages (name, price, selected_test)
        VALUES (%s, %s, %s)
    """, (
        data['name'],
        data['price'],
        selected_tests
    ))
    mysql.connection.commit()
    cur.close()
    end_time = time.time()
    return jsonify({"message": "Package created",
                    "status" : 201,
                    "execution_time": end_time - start_time}), 201


# -------- READ ALL (GET with Search + Pagination) --------
@packages_bp.route('/', methods=['GET'])
@token_required
def get_packages():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # 🔹 query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        filters = ["trash = 0"]  # 🔹 always show non-trash records
        params = []

        if search:
            filters.append("package_name LIKE %s")
            params.append(f"%{search}%")

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        # 🔹 base query
        base_query = f"""
            SELECT *
            FROM test_packages
            {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """

        params.extend([record_per_page, offset])

        cursor.execute(base_query, params)
        packages = cursor.fetchall()

        cursor.close()
        end_time = time.time()

        # 🔹 RESPONSE
        return jsonify({
            "data": packages,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- READ ONE (GET by id) --------
@packages_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_package(id):
    start_time = time.time()
    try:
            mysql = current_app.mysql
            cur = mysql.connection.cursor(DictCursor)
            cur.execute("SELECT selected_test FROM test_packages WHERE id=%s", (id,))
            row = cur.fetchone()
            selected_test = row['selected_test']
            test_ids = [int(t.strip()) for t in selected_test.split(',') if t.strip().isdigit()]
            if not test_ids:
                return jsonify({"error": "No valid test IDs found"}), 400
        
            placeholders = ', '.join(['%s'] * len(test_ids))
            query = f"SELECT id, test_name, delivery_time,sample_required,fee FROM test_profiles WHERE id IN ({placeholders})"
        
            cur.execute(query, tuple(test_ids))
            result = cur.fetchall()
        
            cur.close()
            end_time = time.time()

            return jsonify({
            "status": 200,
            "package_id": id,
            "tests": result,
            "execution_time": end_time - start_time
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)})

# -------- UPDATE (PUT) --------
@packages_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_package(id):
    start_time = time.time()
    
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_package_data(data, is_update=True)
    if error:
        return jsonify({"error": error}), 400
    selected_tests = data.get('selected_test', [])

    selected_tests = ','.join(str(t) for t in selected_tests)
    

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE test_packages
        SET name=%s, price=%s, selected_test=%s
        WHERE id=%s
    """, (
        data.get('name'),
        data.get('price'),
        selected_tests,
        id
    ))
    mysql.connection.commit()
    cur.close()
    end_time = time.time()
    return jsonify({"message": "Package updated",
                    "status" : 200,
                    "execution_time": end_time - start_time})


# -------- DELETE (DELETE) --------
@packages_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_package(id):
    start_time = time.time()
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("UPDATE test_packages SET trash = 1 WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    end_time = time.time()
    return jsonify({"message": "Package deleted",
                    "status" : 200,
                    "execution_time": end_time - start_time})