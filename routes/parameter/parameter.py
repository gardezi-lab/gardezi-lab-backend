from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

parameter_bp = Blueprint('parameter_bp', __name__)

# yahan tumhara pura CRUD code rahega (POST, GET, PUT, DELETE, validate_parameter_data)



# -------- Helper: Simple Validation --------
def validate_parameter_data(data, is_update=False):
    # agar POST hai to required fields check karo
    if not is_update:
        if not data.get("parameter_name"):
            return "parameter_name is required"
        if not data.get("input_type"):
            return "input_type is required"

    # agar input_type diya hai to uski validity check karo
    if data.get("input_type"):
        if data["input_type"] not in ["text", "number", "dropdown"]:
            return "Invalid input_type. Allowed: text, number, dropdown"

    # agar normal_value diya hai to numeric check karo
    if data.get("normal_value"):
        try:
            float(data["normal_value"])
        except ValueError:
            return "normal_value must be numeric"

    # agar default_value diya hai to numeric check karo
    if data.get("default_value"):
        try:
            float(data["default_value"])
        except ValueError:
            return "default_value must be numeric"

    return None  # ✅ valid


# -------- CREATE (POST) --------
@parameter_bp.route('/parameters', methods=['POST'])
def create_parameter():
    from flask import current_app
    mysql = current_app.mysql

    data = request.get_json()
    error = validate_parameter_data(data, is_update=False)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO parameters (parameter_name, sub_heading, input_type, unit, normal_value, default_value)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['parameter_name'],
        data.get('sub_heading'),
        data['input_type'],
        data.get('unit'),
        data.get('normal_value'),
        data.get('default_value')
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Parameter added"}), 201


# -------- READ ALL (GET) --------
@parameter_bp.route('/parameters', methods=['GET'])
def get_parameters():
    from flask import current_app
    mysql = current_app.mysql

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM parameters")
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)


# -------- UPDATE (PUT) --------
@parameter_bp.route('/parameters/<int:id>', methods=['PUT'])
def update_parameter(id):
    from flask import current_app
    mysql = current_app.mysql

    data = request.get_json()
    error = validate_parameter_data(data, is_update=True)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE parameters
        SET parameter_name=%s, sub_heading=%s, input_type=%s, unit=%s, normal_value=%s, default_value=%s
        WHERE id=%s
    """, (
        data.get('parameter_name'),
        data.get('sub_heading'),
        data.get('input_type'),
        data.get('unit'),
        data.get('normal_value'),
        data.get('default_value'),
        id
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Parameter updated"})


# -------- DELETE (DELETE) --------
@parameter_bp.route('/parameters/<int:id>', methods=['DELETE'])
def delete_parameter(id):
    from flask import current_app
    mysql = current_app.mysql

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM parameters WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Parameter deleted"})
