from flask import Blueprint, request, jsonify, current_app

packages_bp = Blueprint('packages_bp', __name__)




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
@packages_bp.route('/packages', methods=['POST'])
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
    return jsonify({"message": "Package created"}), 201


# -------- READ ALL (GET) --------
@packages_bp.route('/packages', methods=['GET'])
def get_packages():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM test_packages")
    rows = cur.fetchall()
    cur.close()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "selected_test": row[3]
        })
    return jsonify(result)


# -------- READ ONE (GET by id) --------
@packages_bp.route('/packages/<int:id>', methods=['GET'])
def get_package(id):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM test_packages WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()

    if row:
        return jsonify({
            "id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "selected_test": row[3]
        })
    return jsonify({"error": "Package not found"}), 404


# -------- UPDATE (PUT) --------
@packages_bp.route('/packages/<int:id>', methods=['PUT'])
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
    return jsonify({"message": "Package updated"})


# -------- DELETE (DELETE) --------
@packages_bp.route('/packages/<int:id>', methods=['DELETE'])
def delete_package(id):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM test_packages WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Package deleted"})
