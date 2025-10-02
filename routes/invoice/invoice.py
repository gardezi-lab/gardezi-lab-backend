from flask import Flask, request, jsonify, Blueprint, current_app
from flask_mysqldb import MySQL
import qrcode
import base64
from io import BytesIO
from datetime import datetime

invoice_bp = Blueprint('invoice', __name__, url_prefix='/api/invoice')
mysql = MySQL()

# ------------------ Invoice API -------------------
@invoice_bp.route('/<int:id>', methods=['GET'])
def generate_invoice(id):
    try:
        cursor = mysql.connection.cursor()

        
        get_query = """
            SELECT patient_name, age, company, email, address, priority, remarks, test 
            FROM patient_entry WHERE id = %s
        """
        cursor.execute(get_query, (id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"status": 404, "message": "Patient not found"}), 404

        patient_data = {
            "patient_name": result[0],
            "age": result[1],
            "company": result[2],
            "email": result[3],
            "address": result[4],
            "priority": result[5],
            "remark": result[6],
            "test": result[7],
            "invoice_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        #  Generate QR code for invoice
        qr_text = f"Invoice for {patient_data['patient_name']} - {patient_data['invoice_date']}"
        qr_img = qrcode.make(qr_text)

        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_url = f"data:image/png;base64,{qr_base64}"

        #  Prepare response JSON
        invoice_data = {
            "status": 200,
            "message": "Invoice generated successfully",
            "patient": patient_data,
            "qr_code": qr_data_url
        }

        return jsonify(invoice_data), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
