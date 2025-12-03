from flask import Blueprint, request, jsonify,current_app
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
import MySQLdb

collectioncenter_bp = Blueprint('collectioncenter', __name__, url_prefix='/api/collectioncenter')

# -------------------- Get all collection centers --------------------
@collectioncenter_bp.route('/', methods=['GET'])
def get_collection_centers():
    try:
        mysql = current_app.mysql      
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM collectioncenter")   
        collection_centers = cursor.fetchall()

        return jsonify(collection_centers), 200

    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()

# ----------------------------------Add collection center-----------------------------
@collectioncenter_bp.route('/', methods=['POST'])
def add_collection_center():
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
        return jsonify({"message": "Collection center added successfully"}), 201
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------Update collection center-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['PUT'])
def update_collection_center(center_id):
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
        return jsonify({"message": "Collection center updated successfully"}), 200
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------Delete collection center-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['DELETE'])
def delete_collection_center(center_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        
        cursor.execute(
            "DELETE FROM collectioncenter WHERE id=%s",
            (center_id,)
        )
        mysql.connection.commit()
        return jsonify({"message": "Collection center deleted successfully"}), 200
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
# ----------------------------------GEt collection center by id-----------------------------
@collectioncenter_bp.route('/<int:center_id>', methods=['GET'])
def get_collection_center(center_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM collectioncenter WHERE id=%s",
            (center_id,)
        )
        collection_center = cursor.fetchone()
        if collection_center:
            return jsonify(collection_center), 200
        else:
            return jsonify({"error": "Collection center not found"}), 404
    except MySQLdb.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()