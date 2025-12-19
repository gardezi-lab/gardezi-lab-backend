from flask import Blueprint, jsonify, send_file, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
from xhtml2pdf import pisa
from datetime import datetime
from io import BytesIO
import qrcode
import base64
import os
import traceback
from routes.authentication.authentication import token_required


invoicepdf_bp = Blueprint('invoicepdf', __name__, url_prefix='/api/invoicepdf')
mysql = MySQL()

INVOICE_FOLDER = "generated_invoices"
os.makedirs(INVOICE_FOLDER, exist_ok=True)

# ---------------- INVOICE HTML ----------------
def generate_invoice_html(patient, counter, tests, qr_data_url, reff_by_name):
    total_fee = 0
    tests_rows = ""
    for t in tests:
        fee = int(t.get("fee") or 0)
        total_fee += fee
        tests_rows += f"""
        <tr>
            <td>{t['test_name']}</td>
            <td>{t.get('reporting_time','')}</td>
            <td>{fee}</td>
        </tr>
        """

    # Calculate discount in Rs (already from counter) and percentage
    discount_percentage = int(counter.get('discount') or 0)  # jo database mein hai
    discount_amount = 0
    if total_fee > 0:
        discount_amount = round((discount_percentage / 100) * total_fee, 2)


    html = f"""
<html>
<head>
    <style>
        @page {{ size:A4; margin: 5mm; }} /* approximate #9 envelope */
        body {{ font-family: Arial, sans-serif; font-size: 10px; line-height:1.3; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        h2 {{ margin:0; font-size:14px; }}
        .info {{ margin-bottom: 8px; }}
        .info div {{ margin-bottom:4px; }}
        .info span {{ display:inline-block; margin-right:10px; min-width: 60px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size:10px; }}
        th, td {{ padding: 3px 2px; border: none; text-align: left; }}
        th {{ border-bottom: 1px solid #000; }}
        p.summary {{ font-size:10px; margin-top:6px; }}
    </style>
</head>
<body>
    <div class="header" style="display:flex; justify-content: space-between; align-items: center; margin-bottom:10px;">
    <div style="flex:1;">
        <h2 style="margin:0; font-size:14px;">GARDEZI LABORATORY</h2>
    </div>
    <div style="flex:0;">
        <img src="{qr_data_url}" width="50" style="float:right;">
    </div>
</div>

    <table style="width:100%; border-collapse: collapse; font-size:12px;">
    <tr>
        <td><b>Name:</b> {patient.get('patient_name','')}</td>
        <td><b>Age:</b> {patient.get('age','')}</td>
    </tr>
    <tr>
        <td><b>Gender:</b> {patient.get('gender','')}</td>
        <td><b>Referred By:</b> {reff_by_name}</td>
    </tr>
    <tr>
        <td><b>Father/Husband:</b> {patient.get('father_husband','')}</td>
        <td><b>MR#:</b> {patient.get('mr_number','')}</td>
    </tr>
    <tr>
        <td><b>Cell:</b> {patient.get('cell','')}</td>
        <td><b>Remarks:</b> {patient.get('remarks','')}</td>
    </tr>
    <tr>
        <td colspan="2"><b>Date:</b> {counter.get('date_created','')}</td>
    </tr>
</table>

    <table>
        <tr>
            <th>Description</th>
            <th>Reporting Time</th>
            <th>Amount</th>
        </tr>
        {tests_rows}
        <tr>
            <td colspan="2" align="right"><b>Total Fee</b></td>
            <td>{total_fee} /-Rs</td>
        </tr>
    </table>

    <p class="summary">
        <b>Total Amount:</b> {total_fee} /-Rs <br>
        <b>Discount:</b> {discount_amount} /-Rs <br>
        <b>Net Amount:</b> {total_fee - discount_amount} /-Rs <br>
        <b>Advance Received:</b> {int(counter.get('paid') or 0)} /-Rs <br>
        <b>Balance Due:</b> {total_fee - int(counter.get('paid') or 0) - discount_amount} /-Rs
    </p>
</body>
</html>
"""
    return html


# ---------------- INVOICE API ----------------
@invoicepdf_bp.route('/<int:id>', methods=['GET'])
@token_required
def generate_invoice_pdf(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Counter
        cursor.execute("SELECT * FROM counter WHERE id=%s", (id,))
        counter = cursor.fetchone()
        
        if not counter:
            return jsonify({"status": 404, "message": "Counter not found"}), 404

        # Patient
        cursor.execute("SELECT * FROM patient_entry WHERE id=%s", (counter["pt_id"],))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"status": 404, "message": "Patient not found"}), 404

        # Referred By
        reff_by_name = "Self"
        if counter.get("reff_by"):
            cursor.execute("SELECT name FROM users WHERE id=%s", (counter["reff_by"],))
            reff = cursor.fetchone()
            if reff:
                reff_by_name = reff["name"]

        # Tests
        cursor.execute("""
            SELECT tp.test_name, tp.fee, pt.reporting_time
            FROM patient_tests pt
            JOIN test_profiles tp ON pt.test_id = tp.id
            WHERE pt.counter_id=%s
        """, (id,))
        tests = cursor.fetchall()

        # QR Code
        qr = qrcode.make(f"Invoice #{id}")
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        # Generate HTML
        html = generate_invoice_html(patient, counter, tests, qr_data_url, reff_by_name)

        # Generate PDF
        filename = f"invoice_{id}_{int(datetime.now().timestamp())}.pdf"
        pdf_path = os.path.join(INVOICE_FOLDER, filename)
        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f)

        pdf_url = url_for("invoicepdf.get_invoice_file", filename=filename, _external=True)
        return jsonify({"status": 200, "pdf_url": pdf_url}), 200

    except Exception as e:
        return jsonify({"status": 500, "error": str(e), "trace": traceback.format_exc()}), 500

# ---------------- SERVE PDF ----------------
@invoicepdf_bp.route('/file/<filename>')
def get_invoice_file(filename):
    path = os.path.join(INVOICE_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"status": 404, "message": "File not found"}), 404
    return send_file(path, mimetype="application/pdf", as_attachment=False)
