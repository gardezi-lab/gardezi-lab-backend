import math, random, string
from flask import Blueprint, request, jsonify, current_app
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
import MySQLdb
import os
from datetime import datetime
import time
from routes.authentication.authentication import token_required


users_bp = Blueprint('users', __name__, url_prefix='/api/users')
mysql = MySQL()

#===================== Users CRUD Operations =====================

#--------------------- User POST -------------------
@users_bp.route('/', methods=['POST'])
@token_required
def create_user():
    start_time = time.time()
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        discount = data.get("discount")
        plain_password = data.get("password")
        if not plain_password:
            plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        age = data.get("age")
        role = data.get("role")
        cc = data.get("cc")

        # Validation
        if not all([name, contact_no, user_name, age, role]):
            return jsonify({"error": "All fields except password are required"}), 400

        if isinstance(name, int) or isinstance(user_name, int):
            return jsonify({"message": "Name  or username cannot be number"}), 400

        insert_query = """
            INSERT INTO users (name, contact_no, user_name, password, role, age, discount, cc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor = mysql.connection.cursor()
        cursor.execute(insert_query, (
            name,
            contact_no,
            user_name,
            plain_password,
            role,
            age,
            discount,
            cc
        ))
        mysql.connection.commit()
        end_time = time.time()

        return jsonify({
            "message": "User created successfully",
            "name": name,
            "contact_no": contact_no,
            "user_name": user_name,
            "role": role,
            "age": age,
            "password": plain_password,
            "discount": discount,
            "cc": cc,
            "execution_time": end_time - start_time
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- Users GET (with Search + Pagination) --------------------
@users_bp.route('/', methods=['GET'])
@token_required
def get_users():
    start_time = time.time()
    try:
        cur = mysql.connection.cursor(DictCursor)

        # query params
        search = request.args.get("search", "", type=str)
        current_page = request.args.get("currentpage", 1, type=int)
        record_per_page = request.args.get("recordperpage", 10, type=int)
        offset = (current_page - 1) * record_per_page

        # base query
        base_query = """
            SELECT id, name, contact_no, user_name, password, role, age, discount, cc
            FROM users
        """
        where_clauses = []
        values = []

        # 🔹 TRASH FILTER (ALWAYS)
        where_clauses.append("trash = 0")

        if search:
            where_clauses.append("(name LIKE %s OR user_name LIKE %s OR role LIKE %s)")
            values.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # total count
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cur.execute(count_query, values)
        total_records = cur.fetchone()["total"]

        # pagination
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        values.extend([record_per_page, offset])
        cur.execute(base_query, values)
        users = cur.fetchall()

        total_pages = math.ceil(total_records / record_per_page)
        end_time = time.time()

        return jsonify({
            "data": users,
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": current_page,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



#---------------------- User Get by ID -------------------
@users_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_user_by_id(id):
    start_time = time.time()
    try:
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("""
            SELECT id, name, contact_no, user_name, password, role, age,discount 
            FROM users WHERE id = %s
        """, (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        return jsonify(row), 200
        end_time = time.time()
        row['execution_time'] = end_time - start_time
        return jsonify(row), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- User Update --------------------
@users_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_user(id):
    start_time = time.time()
    try:
        data = request.get_json()
        name = data.get("name")
        contact_no = data.get("contact_no")
        user_name = data.get("user_name")
        # plain_password = data.get("password")
        role = data.get("role")
        age = data.get("age")
        discount = data.get("discount")

        # Check user exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404

        update_query = """
            UPDATE users
            SET name=%s, contact_no=%s, user_name=%s,  role=%s, age=%s, discount=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (
            name, contact_no, user_name, role, age, discount, id
        ))
        mysql.connection.commit()
        end_time = time.time()

        return jsonify({"message": "User updated successfully", "execution_time": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- User Delete --------------------
@users_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_user(id):
    start_time = time.time()
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s AND trash = 0", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404

        cursor.execute("UPDATE users SET trash = 1 WHERE id = %s", (id,))
        mysql.connection.commit()
        end_time = time.time()
        return jsonify({"message": "User deleted successfully", "execution_time": end_time - start_time}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#----------------- Get Role Wise User List ---------------------
@users_bp.route('/datalist/<string:role_name>', methods=['GET'])
@token_required
def datalist_role(role_name):
    start_time = time.time()
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT role FROM users WHERE role LIKE %s",
            ('%' + role_name + '%',)
        )
        results = cur.fetchall()
        cur.close()

        roles = [{"role_name": r[0]} for r in results]

        if not roles:
            return jsonify({"message": "No roles found"}), 404
        end_time = time.time()
        roles.append()['execution_time'] = end_time - start_time

        return jsonify(roles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#------------------User profile ----------------
@users_bp.route('/user_profile/<int:id>', methods=['GET'])
@token_required
def get_user_profile(id):
    start_time = time.time()
    try:
        cursor = mysql.connection.cursor(DictCursor)
        get_query = "SELECT contact_no, user_name, age, name, email, qualification,profile_pic_path, password  FROM users WHERE id = %s"
        cursor.execute(get_query,(id,))
        data = cursor.fetchone()
        end_time = time.time()
        return jsonify({"data": data, "status": 200, "execution_time": end_time - start_time})
    except Exception as e:
        return jsonify({"error": str(e)})
#----------------------update_user profile---------------
UPLOAD_FOLDER = 'static/profile_pictures'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@users_bp.route('/user_profile/<int:id>', methods=['PUT'])
@token_required
def update_user_profile(id):
    start_time = time.time()
    try:
        name = request.form.get("name")
        contact_no = request.form.get("contact_no")
        user_name = request.form.get("user_name")
        age = request.form.get("age")
        email = request.form.get("email")
        qualification = request.form.get("qualification")
        
        
        profile_pic = request.files.get("profile_pic")

        
        image_path = None
        if profile_pic:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            image_filename = f"user_{id}_{timestamp}.jpg"
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)
            profile_pic.save(image_path)

        # Database operations
        conn = current_app.mysql.connection
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "User not found"}), 404

        # Update user info
        cursor.execute("""
            UPDATE users
            SET name=%s, contact_no=%s, user_name=%s, age=%s, email=%s, qualification=%s,profile_pic_path=%s
            WHERE id=%s
        """, (name, contact_no, user_name, age, email, qualification, image_path,id))
        conn.commit()
        end_time = time.time()

        return jsonify({
            "message": "User updated successfully",
            "profile_pic_path": image_path,
            "status": 200,
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#-------------------- password update ------------
@users_bp.route('/update_password/<int:id>', methods=['PUT'])
@token_required
def update_password(id):
    start_time = time.time()
    try:
        data = request.get_json()
        password  = data.get('password')
        
        conn = mysql.connection
        cursor = conn.cursor()
        update_query = """
            UPDATE users 
            SET password = %s 
            WHERE id = %s"""
        cursor.execute(update_query,(password,id,))
        conn.commit()
        end_time = time.time()
        return jsonify({"message": "password is update succesfuly", "execution_time": end_time - start_time})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-------------------------- GET all users their role is doctor------------------------
@users_bp.route('/doctors/', methods=['GET'])
@token_required
def get_doctors_only():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)   

        #  Sirf doctors ko fetch karna
        query = """
            SELECT 
                id, 
                name, 
                contact_no, 
                user_name, 
                password, 
                role, 
                age 
            FROM users 
            WHERE role = 'Doctor'
        """
        cursor.execute(query)
        doctors = cursor.fetchall()
        cursor.close()
        end_time = time.time()

        return jsonify({
            "data": doctors,
            "count": len(doctors),
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ------------------get all their role is technician  -----------------------
@users_bp.route('/technicians/', methods=['GET'])
@token_required
def get_technicians():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        query = """
            SELECT 
                id, 
                name, 
                contact_no, 
                user_name, 
                password, 
                role, 
                age 
            FROM users 
            WHERE role = 'Technician'
        """
        cursor.execute(query)
        technicians = cursor.fetchall()
        cursor.close()

        return jsonify({
            "data": technicians,
            "count": len(technicians),
            "execution_time": time.time() - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500 


# ---------------------get all users their role is reception-----------------------
@users_bp.route('/receptionists/', methods=['GET'])
@token_required
def get_receptionists_only():
    start_time = time.time()
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # ✅ DictCursor for JSON response

        #  Sirf receptionists ko fetch karna
        query = """
            SELECT 
                id, 
                name, 
                contact_no, 
                user_name, 
                password, 
                role, 
                age,
                cc
            FROM users 
            WHERE role = 'Reception' AND cc IS NOT NULL
        """
        cursor.execute(query)
        receptionists = cursor.fetchall()
        cursor.close()
        end_time = time.time()

        return jsonify({
            "data": receptionists,
            "count": len(receptionists),
            "execution_time": end_time - start_time
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500