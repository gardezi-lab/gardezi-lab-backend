from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL
from utils.pagination import paginate_query

role_bp = Blueprint('role', __name__, url_prefix='/api/role')
mysql = MySQL()

#=====================Role Crud operations=====================#
#---------------------Get all roles---------------------#
@role_bp.route('/', methods=['GET'])
def get_roles():
    try:
        cur = mysql.connection.cursor()
        base_query = "SELECT * FROM roles"
        return jsonify(paginate_query(cur,base_query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#---------------------Get role by ID---------------------#
@role_bp.route('/<int:role_id>', methods=['GET'])
def get_role(role_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        role = cur.fetchone()
        cur.close()
        if role:
            return jsonify(role), 200
        else:
            return jsonify({"error": "Role not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Create a new role---------------------#
@role_bp.route('/', methods=['POST'])
def create_role():
    try:
        data = request.get_json()
        role_name = data.get("role_name")
        if not role_name:
            return jsonify({"error": "Role name is required"}), 400
        #role is mandatory in string format
        if not isinstance(role_name, str):
            return jsonify({"error": "Role name must be a string"}), 400
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO roles (role_name) VALUES (%s)", (role_name,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Update an existing role---------------------#
@role_bp.route('/<int:role_id>', methods=['PUT'])
def update_role(role_id):
    try:
        data = request.get_json()
        role_name = data.get("role_name")
        if not role_name:
            return jsonify({"error": "Role name is required"}), 400
        if not isinstance(role_name, str):
            return jsonify({"error": "Role name must be a string"}), 400
        #if role is not exist then they do not update
        #if role is already exist then they do not update
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM roles WHERE role_name = %s AND id != %s", (role_name, role_id))
        if cur.fetchone():
            return jsonify({"error": "Role already exists"}), 400
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        existing_role = cur.fetchone()
        if not existing_role:
            return jsonify({"error": "Role not found"}), 404
        cur.execute("UPDATE roles SET role_name = %s WHERE id = %s", (role_name, role_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------Delete a role---------------------#
@role_bp.route('/<int:role_id>', methods=['DELETE'])
def delete_role(role_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Role deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#--------------------Search Role by name---------------------#
@role_bp.route('/search/<string:role_name>', methods=['GET'])
def search_role(role_name):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM roles WHERE role_name LIKE %s",
            ('%' + role_name + '%',)
        )
        results = cur.fetchall()
        cur.close()

        roles = []
        for result in results:
            roles.append({
                "id": result[0],
                "role_name": result[1]
            })

        if not roles:
            return jsonify({"message": "No roles found"}), 404

        return jsonify(roles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#===========================================================#

