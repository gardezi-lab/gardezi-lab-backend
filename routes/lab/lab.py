from flask import Blueprint, request, jsonify,current_app
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
import MySQLdb
import time 
from routes.authentication.authentication import token_required

lab_bp = Blueprint('lab', __name__, url_prefix='/api/lab')

@lab_bp.route('/', methods=['GET'])
@token_required
def get_labs():
    start_time = time.time()
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM lab")   
        labs = cursor.fetchall()
        end_time = time.time()
        # execution time is append to labs
        for lab in labs:
            lab['execution_time'] = end_time - start_time

        return jsonify(labs), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        
# ----------------------------------Add lab-----------------------------
@lab_bp.route('/', methods=['POST'])
@token_required
def add_lab():
    start_time = time.time()
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
        end_time = time.time()

        return jsonify({"message": "Lab added successfully", "execution_time": end_time - start_time}), 201

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
# ----------------------------------Update lab-----------------------------
@lab_bp.route('/<int:lab_id>', methods=['PUT'])
@token_required
def update_lab(lab_id):
    start_time = time.time()
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
        end_time = time.time()

        return jsonify({"message": "Lab updated successfully", "execution_time": end_time - start_time}), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
# ----------------------------------Delete lab-----------------------------
@lab_bp.route('/<int:lab_id>', methods=['DELETE'])
@token_required
def delete_lab(lab_id):
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        delete_query = "DELETE FROM lab WHERE id=%s"
        cursor.execute(delete_query, (lab_id,))
        mysql.connection.commit()
        end_time = time.time()

        return jsonify({"message": "Lab deleted successfully", "execution_time": end_time - start_time}), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
# -------------------lab get by id---------------------------
@lab_bp.route('/<int:lab_id>', methods=['GET'])
@token_required
def get_lab_by_id(lab_id):  
    start_time = time.time()
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM lab WHERE id=%s", (lab_id,))   
        lab = cursor.fetchone()

        if lab:
            end_time = time.time()
            lab['execution_time'] = end_time - start_time
            return jsonify(lab), 200
        else:
            return jsonify({"error": "Lab not found"}), 404

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()