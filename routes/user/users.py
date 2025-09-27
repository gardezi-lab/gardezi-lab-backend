import os, base64
import random, string
from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

users_bp = Blueprint('consultant', __name__, url_prefix='/api/users')
mysql = MySQL()

# Load key from env or generate (DO NOT generate on every run in production)

#=====================Users CRUD Operations=====================

#---------------------User POST -------------------
@users_bp.route('/', methods=['POST'])
def create_users_enc():
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        plain_password = data.get("password")
        if not plain_password:
            plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        age = data.get("age")
        role = data.get("role")

        # Example encryption (optional)
        encrypted_password = plain_password  # ya Fernet se encrypt karo agar chaho

        # Validation
        if not all([name, contact_no,  user_name, age, role]):
            return jsonify({"error": "All fields except password are required"}), 400

        if isinstance(name, int)  or isinstance(user_name, int):
            return jsonify({"message": "doctor name, hospital, or username cannot be number"}), 400

        if isinstance(age, str):
            return jsonify({"message": "age cannot be string"}), 400

        # ✅ Fixed insert query with 8 placeholders
        insert_query = """
            INSERT INTO users(name, contact_no,  user_name, password, password_encrypted, role, age)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = mysql.connection.cursor()
        cursor.execute(insert_query, (
            name,
            contact_no,
            user_name,
            plain_password,
            encrypted_password,
            role,
            age
        ))
        mysql.connection.commit()

        return jsonify({
            "message": "User created successfully",
            "name": name,
            "contact_no": contact_no,
            "user_name": user_name,
            "role": role,
            "age": age,
            "password": plain_password
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    

#-------------------Users GET --------------------
@users_bp.route('/', methods=['GET'])
def get_consultants_enc():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, contact_no,  user_name, password, password_encrypted, age,role
            FROM users
        """)
        rows = cursor.fetchall()

        column_names = [desc[0] for desc in cursor.description]
        users = []

        for row in rows:
            d = dict(zip(column_names, row))
            
            # Keep encrypted password as is, no decryption
            d['plain_password'] = d.get('password')  # 👈 just get plain password column
            del d['password']  # agar aap 'password' ko response mein nahi dikhana chahte
            
            users.append(d)

        return jsonify(users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    

#----------------------user Get by ID -------------------
@users_bp.route('/<int:id>', methods=['GET'])
def get_consultant_by_id(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, contact_no,  user_name, password_encrypted,role, age FROM users WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        column_names = [desc[0] for desc in cursor.description]
        d = dict(zip(column_names, row))
        try:
            decrypted = fernet.decrypt(d['password_encrypted'].encode()).decode()
        except Exception:
            decrypted = None
        d['password'] = decrypted
        del d['password_encrypted']
        return jsonify(d), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#-------------------User Update --------------------
@users_bp.route('/<int:id>', methods=['PUT'])
def update_consultant_enc(id):
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        plain_password = data.get("password")
        role = data.get("role")
        if plain_password:
            encrypted = fernet.encrypt(plain_password.encode()).decode()
            password_clause = ", password_encrypted=%s"
            password_value = (encrypted,)
        else:
            password_clause = ""
            password_value = ()

        age = data.get("age")
        
        #if user exists in  the database then update else show error
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        
        update_query = f"""
            UPDATE users
            SET name=%s, contact_no=%s, user_name=%s, age=%s, role=%s
            {password_clause}
            WHERE id=%s
        """
        values = ( name, contact_no, user_name, age, role) + password_value + (id,)
        cursor = mysql.connection.cursor()
        cursor.execute(update_query, values)
        mysql.connection.commit()

        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#-------------------User Delete --------------------
@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_consultant(id):
    try:
        cursor = mysql.connection.cursor()
        #check if the id exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
         # If exists, delete the record
         
        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"message": "user deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#-------------------Users Search by Name --------------------
@users_bp.route('/search/<string:name>', methods=['GET'])  
def search_consultants(name):
    try:
        cursor = mysql.connection.cursor()

        # Search users by name pattern
        search_query = """
            SELECT id, name, contact_no, user_name, password_encrypted, age, role
            FROM users
            WHERE name LIKE %s
        """
        like_pattern = f"%{name}%"
        cursor.execute(search_query, (like_pattern,))
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": "User not found"}), 404

        column_names = [desc[0] for desc in cursor.description]
        users = []
        for row in rows:
            d = dict(zip(column_names, row))
            try:
                decrypted = fernet.decrypt(d['password_encrypted'].encode()).decode()
            except Exception:
                decrypted = None
            d['password'] = decrypted
            del d['password_encrypted']
            users.append(d)

        return jsonify(users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-----------------create api that give return data base user input on role name---------------------#
@users_bp.route('/datalist/<string:role_name>', methods=['GET'])
def datalist_role(role_name):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT role FROM users WHERE role LIKE %s",
            ('%' + role_name + '%',)
        )
        results = cur.fetchall()
        cur.close()
        roles = []
        for list in results:
            roles.append({
                "role_name": list[0]
            })

        if not roles:
            return jsonify({"message": "No roles found"}), 404

        return jsonify(roles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500