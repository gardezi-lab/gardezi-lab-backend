import math
from flask import Flask, request, jsonify, Blueprint, current_app
from MySQLdb.cursors import DictCursor
from flask_mysqldb import MySQL    
from datetime import datetime, timedelta
from datetime import datetime
import MySQLdb
from werkzeug.utils import secure_filename
import json
import random
import os


patient_entry_bp = Blueprint('patient_entry', __name__, url_prefix='/api/patient_entry')
mysql = MySQL()

# ================== Patient Entry CRUD Operations ================== #

# ------------------- TODO Create Patient Entry ------------------ #
@patient_entry_bp.route('/', methods=['POST'])
# from flask import request, jsonify, current_app
def create_patient_entry():
    try:
        data = request.get_json()

        # --- Extract Fields ---
        cell = data.get('cell')
        patient_id_posted = data.get('patient_id_posted')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        company_id = data.get('company_id')
        user_id = data.get('user_id')
        reff_by = data.get('reff_by')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        package_id = data.get('package_id')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        discount = data.get('discount', 0)
        pending_discount=0
        total_fee = data.get('total_fee', 0)
        paid = data.get('paid', 0)
        test_list = data.get('test', [])
        print("Payload received:", data)
        
        #userid ka discount percentage. 
        
        #total amount ka utna percent nikalo
        
        #if allowed dicsount limit is more than given discount 
        
        #dono variables ko change kr do

        # --- Validations ---
        errors = []
        if not patient_name or not str(patient_name).strip():
            errors.append("Patient name is required.")
        if age is None:
            errors.append("Age is required.")
        if not gender or not str(gender).strip():
            errors.append("Gender is required.")
        if not sample or not str(sample).strip():
            errors.append("Sample is required.")
        if not user_id:
            errors.append("users is required.")

        if errors:
            return jsonify({"errors": errors}), 400

        age = str(age)
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        
        #userid ka discount percentage. 
        cursor.execute("SELECT discount FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        user_allowed_discount = result['discount']
        #total amount ka utna percent nikalo
        discount_amount_allowed = (int(total_fee) * int(user_allowed_discount)) / 100
        
        #if allowed dicsount limit is more than given discount 
        if int(discount) > int(discount_amount_allowed):
            pending_discount = discount
            discount = 0
        #dono variables ko change kr do
        
        
        #patient_id_posted

        if patient_id_posted == 0:
            insert_query = """
        INSERT INTO patient_entry 
        (cell, patient_name, father_hasband_MR, age, gender,
        email, address, user_id, package_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
            cursor.execute(insert_query, (
        cell, patient_name, father_hasband_MR, age,
        gender, email, address,
        user_id,  package_id
    ))
            patient_id = cursor.lastrowid
            print("Inserted patient_id:", patient_id)
        else:
            patient_id = patient_id_posted
            print("Existing patient_id:", patient_id)

        insert_counter = """INSERT INTO counter(pt_id,sample, priority, remarks, paid, total_fee, discount, pending_discount, date_created, user_id, reff_by,company_id)VALUES(%s,%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s ,%s)"""
        cursor.execute(insert_counter,(patient_id, sample, priority, remarks, paid, total_fee, discount, pending_discount, user_id, reff_by,company_id))

        counter_id = cursor.lastrowid
        print("counter_id", counter_id)

        prefix = "2025-GL-"
        MR_number = f"{prefix}{patient_id}"

        cursor.execute(
            "UPDATE patient_entry SET MR_number = %s WHERE id = %s",
            (MR_number, patient_id)
        )

        inserted_tests = []
        inserted_tests_names = []

        for test_obj in test_list:
            test_id = test_obj.get("id")
            test_name = test_obj.get("name")
            delivery_time_hours = test_obj.get('testDeliveryTime', 0)
            delivery_datetime = datetime.now() + timedelta(hours=delivery_time_hours)
        
            print("counter id before query", counter_id)
            print("test id before query", test_id)
            cursor.execute("""
                INSERT INTO patient_tests 
                (patient_id, test_id, status, reporting_time, counter_id)
                VALUES (%s, %s, %s,%s, %s)
            """, (patient_id, test_id,"Unverified", delivery_datetime, counter_id,))
            patient_test_id = cursor.lastrowid
            inserted_tests.append({
                "patient_test_id": patient_test_id,
                "test_id": test_id,
                "test_name": test_name,
            })
            inserted_tests_names.append(test_name)
        comma_names = ",".join(inserted_tests_names)

        # --- Step 6: Insert into Cash Table ---
        cursor.execute(
            "INSERT INTO cash (description, dr) VALUES (%s, %s)",
            (MR_number, total_fee)
        )

        now_time = datetime.now()
        pt_entry_log = f"New Patient Entry: Tests: '{comma_names}', Amount: {total_fee}, Discount: {discount}, Paid: {paid}"
        cursor.execute(
            "INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at) VALUES (%s, %s, %s, %s)",
            (patient_id, counter_id, pt_entry_log, now_time)
        )

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Patient entry created successfully",
            "patient_id": patient_id,
            "MR_number": MR_number,
            "tests": inserted_tests,
            "total_fee": total_fee,
            "discount": discount,
            "paid": paid
        }), 201

    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        if 'cursor' in locals():
            try:
                cursor.close()
            except Exception:
                pass
        return jsonify({"error": str(e)}), 500
    
    
#------------------TODO patient cell check if exist-----------------

@patient_entry_bp.route('/cell/<string:cell>', methods=['GET'])
def cell_patient_check(cell):
    #d#ata = request.get_json()
    # cell = data.get("cell")  
    
    if not cell:    
        return jsonify({"error": "cell is required"}), 400

    mysql = current_app.mysql
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = "SELECT * FROM patient_entry WHERE cell = %s"
    cursor.execute(query, (cell,))
    data = cursor.fetchall()
    cursor.close()

    if data:
        return jsonify({"data": data,"status": 200}), 200
    else:
        return jsonify({"message": "No patient found for this cell", "status":404}), 404



#-------------------- TODO GET selected test of patient by patient_id -----------------------

@patient_entry_bp.route('/tests/<int:id>/', methods=['GET'])
def get_patient_tests(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "Counter not found"}), 404

        patient_id = result['pt_id']

        
        query = """
        SELECT 
            pt.id AS patient_test_id,
            tp.id AS test_profile_id,
            tp.test_name,
            tp.serology_elisa
        FROM patient_tests pt
        JOIN test_profiles tp ON pt.test_id = tp.id
        WHERE pt.patient_id = %s AND pt.counter_id = %s
        """
        cursor.execute(query, (patient_id, id,))
        tests = cursor.fetchall()

        cursor.close()

        if not tests:
            return jsonify({"message": "No tests found for this counter"}), 404

        return jsonify({
            "message": "Patient tests fetched successfully",
            "counter_id": id,
            "tests": tests
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------ TODO GET patient selected tests parameter by patient_test_id ---

@patient_entry_bp.route('/test_parameters/<int:test_id>/<int:patient_id>/<int:counter_id>/<string:test_type>', methods=['GET'])
def get_test_parameters(test_id, patient_id, counter_id, test_type): 
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        
        cursor.execute("""
            SELECT id, parameter_name, unit, sub_heading, normalvalue, default_value, input_type
            FROM parameters
            WHERE test_profile_id = %s
        """, (test_id,))
        parameters = cursor.fetchall()

       
        cursor.execute("""
            SELECT parameter_id, result_value,cutoff_value
            FROM patient_results
            WHERE patient_id = %s AND test_profile_id = %s AND counter_id = %s
        """, (patient_id, test_id, counter_id,))
        results = cursor.fetchall()
        
        cursor.execute("""
            SELECT comment,status,result_status
            FROM patient_tests
            WHERE test_id = %s AND counter_id = %s
        """, (test_id,counter_id))
        
        result = cursor.fetchone()
        if result:
            comment = result['comment']
            status = result['status']
            result_status = result['result_status']
            
        
        results_dict = {
        r['parameter_id']: {
            'result_value': r['result_value'],
            'cutoff_value': r.get('cutoff_value')
        }
        for r in results
        }

       
        updated_parameters = []
        for param in parameters:
            parameter_id = param['id']
            
            if parameter_id in results_dict:
             param['default_value'] = results_dict[parameter_id]['result_value']
             param['cutoff_value'] = results_dict[parameter_id]['cutoff_value']
            else:
             param['cutoff_value'] = None 
            
            updated_parameters.append(param)

        cursor.close()

        return jsonify({
            "test_id": test_id,
            "patient_id": patient_id,
            "comment"  : comment,
            "status"  : status,
            "result_status": result_status,
            "test_type" : test_type,
            "parameters": updated_parameters
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------TODO delete file from file table by id--------
@patient_entry_bp.route('/delete_file/<int:test_id>/', methods=['DELETE'])
def delete_file(test_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    print("file table ki delete id", test_id)
    cursor.execute("SELECT patient_test_id FROM files WHERE id = %s", (test_id,))
    pt_test = cursor.fetchone()
    patient_test_id = pt_test['patient_test_id']
    print("patient test id", patient_test_id)
    
    
    cursor.execute("SELECT patient_id, counter_id, test_id FROM patient_tests WHERE id = %s", (patient_test_id,))
    countme = cursor.fetchone()
    patient_id = countme['patient_id']
    counter_id = countme['counter_id']
    tests_id = countme['test_id']
            
    cursor.execute("SELECT test_name FROM test_profiles WHERE id = %s", (tests_id,))
    count = cursor.fetchone()
    test_name_show = count['test_name']
    pt_entry_log = f"File deleted  Test: {test_name_show}"
    cursor.execute("""
                    INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (patient_id, counter_id, pt_entry_log))
    query = "DELETE FROM files WHERE id = %s "
    cursor.execute(query,(test_id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "file is delete successful", "status": 200})

#-------------- TODO Insert file --------------
UPLOAD_FOLDER = 'static/uploads' 
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@patient_entry_bp.route('/file/<int:test_id>', methods=["POST"])
def insert_file(test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        file = request.files.get('file')
        file_path = None
        if file and allowed_file(file.filename):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = secure_filename(file.filename)
            new_filename = f"{timestamp}_{filename}"

            # create uploads folder if not exists
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            file_path = os.path.join(UPLOAD_FOLDER, new_filename)
            file.save(file_path)
            
            # Insert file in files
        if file_path:
            cursor.execute("""
                INSERT INTO files (patient_test_id, file, uploaded_at, filename)
                VALUES (%s, %s,NOW(), %s)
            """, (test_id, file_path, new_filename))
            
            cursor.execute("SELECT patient_id, counter_id, test_id FROM patient_tests WHERE id = %s", (test_id,))
            countme = cursor.fetchone()
            patient_id = countme['patient_id']
            counter_id = countme['counter_id']
            tests_id = countme['test_id']
            
            cursor.execute("SELECT test_name FROM test_profiles WHERE id = %s", (tests_id,))
            count = cursor.fetchone()
            test_name_show = count['test_name']
            pt_entry_log = f"File attached  Test: {test_name_show}"
            cursor.execute("""
                        INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (patient_id, counter_id, pt_entry_log))
            
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "file uploaded  successfully",
            "file_path": file_path,
            "status": 201
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)})
            
#-------------------TODO Get files ----------------
@patient_entry_bp.route('/get_file/<int:test_id>', methods=['GET'])
def get_files_by(test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        query = "SELECT * FROM files WHERE patient_test_id = %s"
        cursor.execute(query,(test_id,))
        result = cursor.fetchall()
        print("resutl", result)
        return jsonify({"data": result, "status": 200})
    except Exception as e:
        return jsonify({"error": str(e)})
    
        
# helo
        
#---------------------TODO Add result of patient selected test parameters by patient_test_id----

@patient_entry_bp.route('/test_results/<int:id>', methods=['POST'])
def add_or_update_result(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        data = request.get_json()
        parameters = data.get("parameters", [])
        test_profile_id = data.get("test_profile_id")
        comment = data.get("comment")
        
        
        cursor.execute("""
            SELECT c.pt_id AS patient_id, pt.id AS patient_test_id 
            FROM counter c
            JOIN patient_tests pt ON pt.patient_id = c.pt_id AND pt.counter_id = c.id
            WHERE c.id = %s
        """, (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Counter not found or no tests linked"}), 404

        patient_id = result['patient_id']
        patient_test_id = result['patient_test_id']

        # --- Validation ---
        if not parameters:
            return jsonify({"error": "No parameters provided"}), 400

     
        for res in parameters:
            parameter_id = res.get("parameter_id")
            result_value = res.get("result_value", None)
            cutoff_value = res.get("cutoff_value", None)

        
            cursor.execute("""
                SELECT id, test_profile_id FROM patient_results
                WHERE patient_test_id = %s AND parameter_id = %s AND patient_id = %s AND counter_id = %s
            """, (patient_test_id, parameter_id, patient_id, id))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE patient_results
                    SET result_value = %s, cutoff_value = %s
                    WHERE id = %s
                """, (result_value, cutoff_value, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO patient_results
                    (patient_id, patient_test_id, parameter_id, result_value, cutoff_value, created_at, test_profile_id, is_completed, counter_id)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s, 0, %s)
                """, (patient_id, patient_test_id, parameter_id, result_value, cutoff_value, test_profile_id, id))

                # comment add update 
        cursor.execute("""
                            UPDATE patient_tests
                            SET comment = %s, result_status=1
                            WHERE test_id = %s AND counter_id = %s
                        """, (comment, test_profile_id, id))
        
                       #agar all verified ho gae hen to then counter ka status change kr do.
        cursor.execute("SELECT COUNT(*) AS total FROM patient_tests WHERE result_status=0 AND counter_id = %s", (id,))
        count = cursor.fetchone()['total']
        if count == 0:
             cursor.execute("UPDATE counter SET status = 1 WHERE id = %s", (id,))


            # ---  Insert into patient_activity_log ---
        cursor.execute("SELECT test_name FROM test_profiles WHERE id = %s", (test_profile_id,))
        count = cursor.fetchone()
        test_name_show = count['test_name']
        pt_entry_log = f"Result updated for Tests: {test_name_show}"

        cursor.execute("""
                INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (patient_id, id, pt_entry_log))

        
        
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Results saved successfully",
            "test_profile_id": test_profile_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#------------------- TODO Update the test fees --------------

@patient_entry_bp.route("/discount_approvel/<int:id>", methods=["PUT"])
def discount_approvel(id):
    try:
        data = request.get_json()
        discount = int(data.get("discount"))
        user_id = int(data.get("user_id"))
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        
        cursor.execute("UPDATE counter SET discount = %s, pending_discount = %s, discount_approved_by = %s WHERE id=%s", (discount, 0, user_id, id))
        mysql.connection.commit()
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        count = cursor.fetchone()
        pt_id_show = count['pt_id']
        pt_entry_log = f"Discount approved, Discount: {discount}"

        cursor.execute("""
                INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (pt_id_show, id, pt_entry_log))
        
        mysql.connection.commit()


        return jsonify({"message": "Updated", "discount": discount}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500        
#----------------TODO Discount Approvel  --------------

@patient_entry_bp.route("/update_fee/<int:id>", methods=["PUT"])
def update_fee(id):
    try:
        data = request.get_json()
        new_paid = int(data.get("paid"))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT paid, total_fee FROM counter WHERE id=%s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"message": "Record not found"}), 404

        old_paid = int(result['paid'])
        total_fee = int(result['total_fee'])

        total_paid = old_paid + int(new_paid)
        paid = total_paid
        
        cursor.execute("UPDATE counter SET paid = %s WHERE id=%s", (total_paid, id))
        mysql.connection.commit()
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        count = cursor.fetchone()
        pt_id_show = count['pt_id']
        pt_entry_log = f"Amount received, Amount: {new_paid}"

        cursor.execute("""
                INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (pt_id_show, id, pt_entry_log))
        
        mysql.connection.commit()


        return jsonify({"message": "Updated", "paid": total_paid,"total": total_fee}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500        

# ------------------- TODO Get All Patient Entries (Search + Pagination) ------------------ #

@patient_entry_bp.route('/', methods=['GET'])
def get_all_patient_entries():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)
        
        patient_name = request.args.get("patient_name", "", type=str)
        mr_number = request.args.get("mr_number", "", type=str)
        cell = request.args.get("cell", "",type=str)
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        
        filters = []
        params = []
        
        if patient_name:
            filters.append("pt.patient_name LIKE %s")
            params.append(f"%{patient_name}%")

        if mr_number:
            filters.append("pt.mr_number LIKE %s")
            params.append(f"%{mr_number}%")
        if cell:
            filters.append("pt.cell LIKE %s")
            params.append(f"%{cell}%")
        if from_date and to_date:
            filters.append("DATE(pt.created_at) BETWEEN %s AND %s")
            params.extend([from_date, to_date])
        elif from_date:
            filters.append("DATE(pt.created_at) >= %s")
            params.append(from_date)
        elif to_date:
            filters.append("DATE(pt.created_at) <= %s")
            params.append(to_date)

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        base_query = (f"""
        SELECT 
            c.pt_id AS id,
            c.id AS cid,
            c.*,
            pt.*
        FROM counter c
        JOIN patient_entry pt ON c.pt_id = pt.id
        {where_clause}
        ORDER BY c.id DESC
    """)
        cursor.execute(base_query,params)
        patient_data_list = cursor.fetchall()
    
        for patient in patient_data_list:
            print("patiennt id", patient["id"] )
            print("counter id", patient["cid"] )
            cursor.execute("""
                SELECT 
                    pt.id AS patient_test_id, 
                    tp.test_name,
                    tp.delivery_time,
                    tp.sample_required, 
                    tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id = tp.id
                WHERE pt.patient_id = %s AND pt.counter_id=%s
            """, (patient["id"],patient["cid"],))
            tests = cursor.fetchall()
            patient["tests"] = tests

        return jsonify({
            "patients": patient_data_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- TODO Get Patient Entry by ID ------------------ #

@patient_entry_bp.route('/<int:id>', methods=['GET'])
def patient_get_by_id(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)


        cursor.execute("""
            SELECT 
                c.id AS id,
                c.reff_by,
                c.pt_id AS patient_id,
                c.total_fee, 
                c.paid ,
                c.discount ,
                c.sample ,
                c.priority ,
                c.remarks ,
                c.company_id ,
                pt.*
            FROM counter c
            JOIN patient_entry pt ON c.pt_id = pt.id
            WHERE c.id = %s
        """, (id,))
        patient = cursor.fetchone()

        if not patient:
            cursor.close()
            return jsonify({"error": "Patient entry not found"}), 404

        
        cursor.execute("""
            SELECT 
                pt.id AS patient_test_id,
                pt.test_id AS test_id,
                tp.test_name,
                tp.sample_required,
                tp.delivery_time,
                tp.fee
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pt.patient_id = %s AND counter_id= %s
        """, (patient["patient_id"], patient["id"],))
        tests = cursor.fetchall()

        # Attach tests to patient info
        patient["tests"] = tests

        cursor.close()
        
        return jsonify([patient]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- TODo Update Patient Entry by ID ------------------ #

@patient_entry_bp.route('/<int:id>', methods=['PUT'])
def update_patient_entry(id):
    try:
        data = request.get_json()
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Invalid counter ID"}), 404

        patient_id = result["pt_id"]

        
        cell = data.get('cell')
        patient_name = data.get('patient_name')
        father_hasband_MR = data.get('father_hasband_MR')
        age = data.get('age')
        gender = data.get('gender')
        email = data.get('email')
        address = data.get('address')
        sample = data.get('sample')
        priority = data.get('priority')
        remarks = data.get('remarks')
        discount = data.get('discount')
        paid = data.get('paid')
        total_fee = data.get('total_fee')
        company_id = data.get('company_id')
        package_id = data.get('package_id')
        reff_by = data.get('reff_by')
        user_id = data.get('user_id')
        tests = data.get('test', [])  
        print("tests",tests)

        
        update_query = """
            UPDATE patient_entry
            SET cell=%s, patient_name=%s, father_hasband_MR=%s, age=%s, gender=%s,
                email=%s, address=%s,
                package_id=%s, user_id=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (
            cell, patient_name, father_hasband_MR, age, gender, email, address,
            package_id, user_id, patient_id  
        ))

        
        counter_update = """
            UPDATE counter 
            SET total_fee=%s, paid=%s, discount=%s, remarks=%s, priority=%s, sample=%s , reff_by=%s,company_id=%s 
            WHERE pt_id=%s
        """
        cursor.execute(counter_update, (
            total_fee, paid, discount, remarks, priority, sample, reff_by,company_id, patient_id  
        ))

        
        cursor.execute("DELETE FROM patient_tests WHERE patient_id = %s AND  counter_id = %s", (patient_id,id,))

        inserted_tests_names = []
        
        for test in tests:
            test_name = test.get('name')
            delivery_time_hours = test.get('testDeliveryTime', 0)
            delivery_datetime = datetime.now() + timedelta(hours=delivery_time_hours)
            test_id = test.get('id')
            print("Inserting test:", test_id)
            cursor.execute("""
                INSERT INTO patient_tests (patient_id, test_id, reporting_time,counter_id)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, test_id, delivery_datetime, id,))
            
            inserted_tests_names.append(test_name)
            comma_names = ",".join(inserted_tests_names)
            
        now_time = datetime.now()
        pt_entry_log = f"Patient Updated: Tests: '{comma_names}', Amount: {total_fee}, Discount: {discount}, Paid: {paid}"
        
        cursor.execute(
            "INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at) VALUES (%s, %s, %s, %s)",
            (patient_id, id, pt_entry_log, now_time)
        )

        
        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Patient entry aur test_profiles dono update ho gaye",
            "status": 200
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------- TODO Delete Patient Entry by ID ------------------ #

@patient_entry_bp.route('/<int:id>', methods=['DELETE'])
def delete_patient_entry(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()

        
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "Counter record not found", "status": 404}), 404

        patient_id = result[0]
        
        cursor.execute("DELETE FROM counter WHERE id = %s", (id,))
        #cursor.execute("DELETE FROM patient_entry WHERE id = %s", (patient_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Patient entry deleted successfully", "status": 200}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-------------------------#TODO Test Verify ---------------------------------

@patient_entry_bp.route('/verify_test/<int:test_id>', methods=['PUT'])
def verify_test(test_id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        data = request.get_json()
        counter_id = data.get("counter_id")
        user_id = data.get("user_id")
        code = int(data.get("code", 0))
        verified_sts = "Unverified" if code == 0 else "Verified"

        cursor.execute("""
            UPDATE patient_tests
            SET status = %s, verified_at = now(), verified_by = %s
            WHERE counter_id = %s AND test_id = %s
        """, (code, user_id, counter_id, test_id))
        #ham  ne dekhna he k es counter id ki koi test abhi tak 0 matlab unverified he
        #if yes. mean han unverfied hen to counter ka stuatus unverified rakho.
        #agar all verified ho gae hen to then counter ka status change kr do.
        cursor.execute("SELECT COUNT(*) AS total FROM patient_tests WHERE status=0 AND counter_id = %s", (counter_id,))
        count = cursor.fetchone()['total']
        if count > 0:
             cursor.execute("UPDATE counter SET status = 1 WHERE id = %s", (counter_id,))
        else:
             cursor.execute("UPDATE counter SET status = 2 WHERE id = %s", (counter_id,))
        cursor.execute("SELECT test_name FROM test_profiles WHERE id = %s", (test_id,))
        count = cursor.fetchone()
        test_name_show = count['test_name']
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (counter_id,))
        count = cursor.fetchone()
        pt_id = count['pt_id']
        pt_entry_log = f" {verified_sts}, Test: {test_name_show}"
        cursor.execute("""
                        INSERT INTO patient_activity_log (patient_id, counter_id, activity, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (pt_id, counter_id, pt_entry_log))

        mysql.connection.commit()
        cursor.close()

        return jsonify({
            "message": "Status updated successfully",
            "test_id": test_id,
            "counter_id": counter_id,
            
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
 

#------------------------------- #TODO GET Unverifyed data --------------------

@patient_entry_bp.route('/unverified_tests', methods=['GET'])
def get_unverified_tests():
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Optional: filter by patient_id
        patient_id = request.args.get('patient_id')

        if patient_id:
            query = "SELECT * FROM patient_tests WHERE patient_id = %s AND status = 'unverified'"
            cursor.execute(query, (patient_id,))
        else:
            query = "SELECT * FROM patient_tests WHERE status = 'unverified'"
            cursor.execute(query)

        results = cursor.fetchall()
        cursor.close()

        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#---------------------- #TODO GET patient activiety ------------------

@patient_entry_bp.route('/activity/<int:patient_id>', methods=['GET'])
def get_patient_activity(patient_id): 
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor(DictCursor)

        # --- Fetch all activities for this patient ---
        cursor.execute("""
            SELECT activity,  created_at
            FROM patient_activity_log
            WHERE counter_id = %s
            ORDER BY created_at ASC
        """, (patient_id,))
        activities = cursor.fetchall()

        cursor.close()

        return jsonify({
            "patient_id": patient_id,
            "activities": activities,
            "total_activities": len(activities)
        }), 200

    except Exception as e:
        print("Error in get_patient_activity:", str(e))
        return jsonify({"error": str(e)}), 500


 # ---------------- TODO Patient, tests, counter, activity_log, results all are deleted by counter id ----------------------

@patient_entry_bp.route('/all_delete/<int:id>', methods=['DELETE'])
def delete_alldata_patient(id):
    try:
        mysql = current_app.mysql
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT pt_id FROM counter WHERE id = %s", (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "Counter record not found", "status": 404}), 404

        patient_id = result[0]
        
        cursor.execute("DELETE FROM counter WHERE id = %s", (id,))
        cursor.execute("DELETE FROM patient_entry WHERE id = %s", (patient_id,))
        cursor.execute("DELETE FROM patient_activity_log WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM patient_tests WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM patient_results WHERE patient_id = %s", (patient_id,))
        
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Delete successfully all data of patient", "status": 200}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
