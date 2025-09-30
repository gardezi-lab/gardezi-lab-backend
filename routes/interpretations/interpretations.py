from flask import Blueprint, request, jsonify, current_app
from MySQLdb.cursors import DictCursor   
from utils.pagination import paginate_query

# Blueprint with API prefix
interpretation_bp = Blueprint("interpretations", __name__, url_prefix="/api/interpretations")

# -------- Helper: Simple Validation --------
def validate_interpretation_data(data, is_update=False):
    if not is_update:
        if not data.get("type"):
            return "type is required"
        if not data.get("code"):
            return "code is required"
        if not data.get("heading"):
            return "heading is required"
    return None

# -------- CREATE --------
@interpretation_bp.route("/", methods=["POST"])
def create_interpretation():
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_interpretation_data(data, is_update=False)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO interpretations (type, code, heading, detail) VALUES (%s, %s, %s, %s)",
        (data["type"], data["code"], data["heading"], data.get("detail")),
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Interpretation added"}), 201

# -------- READ ALL --------
@interpretation_bp.route("/", methods=["GET"])
def get_interpretations():
    mysql = current_app.mysql
    cur = mysql.connection.cursor(DictCursor)
    base_query = "SELECT * FROM interpretations"
    return jsonify(paginate_query(cur, base_query)), 200

# -------- UPDATE --------
@interpretation_bp.route("/<int:id>", methods=["PUT"])
def update_interpretation(id):
    mysql = current_app.mysql
    data = request.get_json()

    error = validate_interpretation_data(data, is_update=True)
    if error:
        return jsonify({"error": error}), 400

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE interpretations SET type=%s, code=%s, heading=%s, detail=%s WHERE id=%s",
        (data.get("type"), data.get("code"), data.get("heading"), data.get("detail"), id),
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Interpretation updated"})

# -------- DELETE --------
@interpretation_bp.route("/<int:id>", methods=["DELETE"])
def delete_interpretation(id):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM interpretations WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Interpretation deleted"})
