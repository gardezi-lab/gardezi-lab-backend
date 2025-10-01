from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
from utils.pagination import paginate_query


patient_entry_bp = Blueprint('patient_entry', __name__, url_prefix='/api/patient_entry')
mysql = MySQL()

#================== patient Entry Crud Operations ==================#
#------------------- Create Patient Entry ------------------#
@patient_entry_bp.route('/', methods=['POST'])
def create_patient_entry():
    try:
        data = request.get_json()
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test = data.get('test')
        
        if not cell or not patient_name or not father_hasband_MR or not age or not company or not reffered_by or not gender or not email or not address or not package or not sample or not priority or not remarks or not test:
            return jsonify({"error": "All fields are required"}), 400
        if not isinstance(cell, str) or not isinstance(patient_name, str) or not isinstance(father_hasband_MR, str) or not isinstance(age, int) or not isinstance(company, str) or not isinstance(reffered_by, str) or not isinstance (gender, str) or not isinstance(email, str) or not isinstance(address, str) or not isinstance(package, str) or not isinstance(sample, str) or not isinstance(priority, str) or not isinstance(remarks, str) or not isinstance(test, str):
            errors = []
            if not isinstance(cell, str):
                errors.append("cell must be a string")
            if not isinstance(patient_name, str):
                errors.append("patient_name must be a string")
            if not isinstance(father_hasband_MR, str):
                errors.append("father_hasband_MR must be a string")
            if not isinstance(age, int):
                errors.append("age must be an integer")
            if not isinstance(company, str):
                errors.append("company must be a string")
            if not isinstance(reffered_by, str):
                errors.append("reffered_by must be a string")
            if not isinstance(gender, str):
                errors.append("gender must be a string")
            if not isinstance(email, str):
                errors.append("email must be a string")
            if not isinstance(address, str):
                errors.append("address must be a string")
            if not isinstance(package, str):
                errors.append("package must be a string")
            if not isinstance(sample, str):
                errors.append("sample must be a string")
            if not isinstance(priority, str):
                errors.append("priority must be a string")
            if not isinstance(remarks, str):
                errors.append("remarks must be a string")
            if not isinstance(test, str):
                errors.append("test must be a string")
            return jsonify({"errors": errors}), 400
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        insert_query = """
            INSERT INTO patient_entry (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test))
        mysql.connection.commit()
        cursor.close()

        return jsonify({
    "message": "Patient entry created successfully",
    "id": cursor.lastrowid,
    "cell": cell,
    "patient_name": patient_name,
    "father_hasband_MR": father_hasband_MR,
    "age": age,
    "company": company,
    "reffered_by": reffered_by,
    "gender": gender,
    "email": email,
    "address": address,
    "package": package,
    "sample": sample,
    "priority": priority,
    "remarks": remarks,
    "test": test
}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- Get All Patient Entry ------------------#
@patient_entry_bp.route('/', methods=['GET'])
def get_all_patient_entries():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        base_query = "SELECT * FROM patient_entry"
        return jsonify({
            "data" : paginate_query(cursor, base_query),
            "status" : 200})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- Get Patient Entry by ID ------------------#
@patient_entry_bp.route('/<int:id>', methods=['GET'])
def patient_get_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM patient_entry WHERE id = %s", (id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            patient_entry = {
                "id": row[0],
                "cell": row[1],
                "patient_name": row[2],
                "father_hasband_MR": row[3],
                "age": row[4],
                "company": row[5],
                "reffered_by": row[6],
                "gender": row[7],
                "email": row[8],
                "address": row[9],
                "package": row[10],
                "sample": row[11],
                "priority": row[12],
                "remarks": row[13],
                "test": row[14],
                "status" : 200
            }
            return jsonify({"patient_entry": patient_entry}), 200
        return jsonify({"error": "Patient entry not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- Update Patient Entry by ID ------------------#
@patient_entry_bp.route('/<int:id>', methods=['PUT'])
def update_patient_entry(id):
    try:
        data = request.get_json()
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company = data.get('company')
        reffered_by = data.get('reffered_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package = data.get('package')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        test = data.get('test')

        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        update_query = """
            UPDATE patient_entry
            SET cell = %s, patient_name = %s, father_hasband_MR = %s, age = %s, company = %s,
                reffered_by = %s, gender = %s, email = %s, address = %s, package = %s,
                sample = %s, priority = %s, remarks = %s, test = %s
            WHERE id = %s
        """
        cursor.execute(update_query, (cell, patient_name, father_hasband_MR, age, company, reffered_by, gender, email, address, package, sample, priority, remarks, test, id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry updated successfully",
                        "status": 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#------------------- Delete Patient Entry by ID ------------------#
@patient_entry_bp.route('/<int:id>', methods=['DELETE'])
def delete_patient_entry(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM patient_entry WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient entry deleted successfully",
                        "status" : 200}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#=================================================================#