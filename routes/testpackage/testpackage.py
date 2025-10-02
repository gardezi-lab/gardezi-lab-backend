import math
from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor

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
def create_package():
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_package_data(data, is_update=False)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO test_packages (name, price, selected_test)
        VALUES (%s, %s, %s)
    """, (
        data['name'],
        data['price'],
        data['selected_test']
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Package created",
                    "status" : 201}), 201


# -------- READ ALL (GET with Search + Pagination) --------
@packages_bp.route('/', methods=['GET'])
def get_packages():
    try:
        mysql = current_app.mysql
        cur = mysql.connection.cursor(DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)

        offset = (current_page - 1) * record_per_page

        # base query
        base_query = "SELECT * FROM test_packages"
        where_clauses = []
        values = []

        if search:
            where_clauses.append("(name LIKE %s OR selected_test LIKE %s)")
            values.extend([f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # count total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cur.execute(count_query, values)
        total_records = cur.fetchone()["total"]

        # pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cur.execute(base_query, values)
        packages = cur.fetchall()

        total_pages = math.ceil(total_records / record_per_page)

        return jsonify({
            "data": packages,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- READ ONE (GET by id) --------
@packages_bp.route('/<int:id>', methods=['GET'])
def get_package(id):
    mysql = current_app.mysql
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM test_packages WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()

    if row:
        return jsonify(row), 200
        return jsonify({
            "id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "selected_test": row[3],
            "status" : 200
        })
    return jsonify({"error": "Package not found"}), 404


# -------- UPDATE (PUT) --------
@packages_bp.route('/<int:id>', methods=['PUT'])
def update_package(id):
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_package_data(data, is_update=True)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE test_packages
        SET name=%s, price=%s, selected_test=%s
        WHERE id=%s
    """, (
        data.get('name'),
        data.get('price'),
        data.get('selected_test'),
        id
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Package updated",
                    "status" : 200})


# -------- DELETE (DELETE) --------
@packages_bp.route('/<int:id>', methods=['DELETE'])
def delete_package(id):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM test_packages WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Package deleted"})
    return jsonify({"message": "Package deleted",
                    "status" : 200})
