import os, base64
import random, string
from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

consultant_bp = Blueprint('consultant', __name__, url_prefix='/api/consultant')
mysql = MySQL()

# Load key from env or generate (DO NOT generate on every run in production)

#=====================Consultant CRUD Operations=====================
#---------------------Consultant POST -------------------
@consultant_bp.route('/', methods=['POST'])
def create_consultant_enc():
    try:
        data = request.get_json()
        doctor_name = data.get("doctor_name")
        contact_no = data.get("contact_no")
        hospital = data.get("hospital")
        user_name = data.get("user_name")

        plain_password = data.get("password")
        if not plain_password:
            plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # encrypt
        encrypted = fernet.encrypt(plain_password.encode()).decode()

        age = data.get("age")
        insert_query = """
            INSERT INTO consultants(doctor_name, contact_no, hospital, user_name, password, password_encrypted, age)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = mysql.connection.cursor()
        cursor.execute(insert_query, (doctor_name, contact_no, hospital, user_name,plain_password, encrypted, age))
        mysql.connection.commit()

        return jsonify({
            "message": "Consultant created  successfully",
            "doctor_name": doctor_name,
            "age" : age,
            "contact_no": contact_no,
            "hospital": hospital,
            "user_name": user_name,
            "password": plain_password   
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#-------------------Consultant GET --------------------
@consultant_bp.route('/', methods=['GET'])
def get_consultants_enc():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, doctor_name, contact_no, hospital, user_name, password_encrypted, age FROM consultants")
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        consultants = []
        for row in rows:
            d = dict(zip(column_names, row))
            # decrypt password (risky) and include plain in response
            try:
                decrypted = fernet.decrypt(d['password_encrypted'].encode()).decode()
            except Exception:
                decrypted = None
            d['password'] = decrypted
            del d['password_encrypted']
            consultants.append(d)
        return jsonify(consultants), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#----------------------Consultant Get by ID -------------------
@consultant_bp.route('/<int:id>', methods=['GET'])
def get_consultant_by_id(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, doctor_name, contact_no, hospital, user_name, password_encrypted, age FROM consultants WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Consultant not found"}), 404
        column_names = [desc[0] for desc in cursor.description]
        d = dict(zip(column_names, row))
        # decrypt password (risky) and include plain in response
        try:
            decrypted = fernet.decrypt(d['password_encrypted'].encode()).decode()
        except Exception:
            decrypted = None
        d['password'] = decrypted
        del d['password_encrypted']
        return jsonify(d), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------Consultant Update --------------------
@consultant_bp.route('/<int:id>', methods=['PUT'])
def update_consultant_enc(id):
    try:
        data = request.get_json()
        doctor_name = data.get("doctor_name")
        contact_no = data.get("contact_no")
        hospital = data.get("hospital")
        user_name = data.get("user_name")

        plain_password = data.get("password")
        if plain_password:
            encrypted = fernet.encrypt(plain_password.encode()).decode()
            password_clause = ", password_encrypted=%s"
            password_value = (encrypted,)
        else:
            password_clause = ""
            password_value = ()

        age = data.get("age")
        update_query = f"""
            UPDATE consultants
            SET doctor_name=%s, contact_no=%s, hospital=%s, user_name=%s, age=%s
            {password_clause}
            WHERE id=%s
        """
        values = (doctor_name, contact_no, hospital, user_name, age) + password_value + (id,)
        cursor = mysql.connection.cursor()
        cursor.execute(update_query, values)
        mysql.connection.commit()

        return jsonify({"message": "Consultant updated (encrypted) successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------Consultant Delete --------------------
@consultant_bp.route('/<int:id>', methods=['DELETE'])
def delete_consultant(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM consultants WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"message": "Consultant deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------Consultant Search by Name --------------------
@consultant_bp.route('/search/<string:name>', methods=['GET'])  
def search_consultants(name):
    try:
        cursor = mysql.connection.cursor()
        search_query = """
            SELECT id, doctor_name, contact_no, hospital, user_name, password_encrypted, age
            FROM consultants
            WHERE doctor_name LIKE %s
        """
        like_pattern = f"%{name}%"
        cursor.execute(search_query, (like_pattern,))
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        consultants = []
        for row in rows:
            d = dict(zip(column_names, row))
            # decrypt password (risky) and include plain in response
            try:
                decrypted = fernet.decrypt(d['password_encrypted'].encode()).decode()
            except Exception:
                decrypted = None
            d['password'] = decrypted
            del d['password_encrypted']
            consultants.append(d)
        return jsonify(consultants), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500