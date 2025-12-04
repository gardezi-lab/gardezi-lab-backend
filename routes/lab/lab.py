from flask import Blueprint, request, jsonify,current_app
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
import MySQLdb

lab_bp = Blueprint('lab', __name__, url_prefix='/api/lab')

@lab_bp.route('/', methods=['GET'])
def get_labs():
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM lab")   
        labs = cursor.fetchall()

        return jsonify(labs), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        
# ----------------------------------Add lab-----------------------------
@lab_bp.route('/', methods=['POST'])
def add_lab():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        email = data.get("email")
        location = data.get("location")

        insert_query = "INSERT INTO lab (name, contact_no, email, location) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (name, contact_no, email, location))
        mysql.connection.commit()

        return jsonify({"message": "Lab added successfully"}), 201

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
# ----------------------------------Update lab-----------------------------
@lab_bp.route('/<int:lab_id>', methods=['PUT'])
def update_lab(lab_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        email = data.get("email")
        location = data.get("location")

        update_query = """
            UPDATE lab
            SET name=%s, contact_no=%s, email=%s, location=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (name, contact_no, email, location, lab_id))
        mysql.connection.commit()

        return jsonify({"message": "Lab updated successfully"}), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
# ----------------------------------Delete lab-----------------------------
@lab_bp.route('/<int:lab_id>', methods=['DELETE'])
def delete_lab(lab_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        delete_query = "DELETE FROM lab WHERE id=%s"
        cursor.execute(delete_query, (lab_id,))
        mysql.connection.commit()

        return jsonify({"message": "Lab deleted successfully"}), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
# -------------------lab get by id---------------------------
@lab_bp.route('/<int:lab_id>', methods=['GET'])
def get_lab_by_id(lab_id):  
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM lab WHERE id=%s", (lab_id,))   
        lab = cursor.fetchone()

        if lab:
            return jsonify(lab), 200
        else:
            return jsonify({"error": "Lab not found"}), 404

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()