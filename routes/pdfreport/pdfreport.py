# pdfreport.py
from flask import Blueprint, request, url_for, current_app, jsonify, send_file
from flask_mysqldb import MySQL
import qrcode
from io import BytesIO
from datetime import datetime
import MySQLdb.cursors
from xhtml2pdf import pisa
import os
import base64
import traceback

pdfreport_bp = Blueprint('pdfreport', __name__, url_prefix='/api/pdfreport')
mysql = MySQL()
PDF_FOLDER = 'generated_reports'
os.makedirs(PDF_FOLDER, exist_ok=True)


def build_parameters(cursor, patient_id, counter_id, test_id):
    cursor.execute("""
        SELECT c.date_created AS test_datetime, p.parameter_name, p.unit, p.normalvalue, pr.result_value, pr.cutoff_value, p.sub_heading
        FROM parameters p
        JOIN patient_tests pt ON p.test_profile_id = pt.test_id AND pt.patient_id=%s AND pt.counter_id <= %s
        JOIN patient_results pr ON pr.parameter_id = p.id AND pr.counter_id = pt.counter_id
        JOIN counter c ON pt.counter_id = c.id
        WHERE pt.test_id=%s
        ORDER BY c.date_created ASC
    """, (patient_id, counter_id, test_id))
    
    rows = cursor.fetchall() or []
    dates = sorted(list({str(r['test_datetime']) for r in rows}))
    
    params_map = {}
    for r in rows:
        pname = r['parameter_name']
        if pname not in params_map:
            params_map[pname] = {
                "unit": r.get('unit'),
                "normalvalue": r.get('normalvalue'),
                "sub_heading": r.get('sub_heading'),
                "results": {},
                "cutoffs": {}
            }
        params_map[pname]["results"][str(r['test_datetime'])] = r.get('result_value')
        params_map[pname]["cutoffs"][str(r['test_datetime'])] = r.get('cutoff_value')

    parameters = []
    for pname, pdata in params_map.items():
        results = [pdata["results"].get(d, "-") for d in dates]
        cutoffs = [pdata["cutoffs"].get(d, "-") for d in dates]
        parameters.append({
            "parameter_name": pname,
            "unit": pdata.get("unit"),
            "normalvalue": pdata.get("normalvalue"),
            "sub_heading": pdata.get("sub_heading"),
            "result_value": results,
            "cutoff_value": cutoffs
        })
    return dates, parameters


def render_parameters_html(test):
    params = test.get('parameters', [])
    if not params:
        return "<p>No parameters available</p>"
    
    dates = test.get('dates', [])
    html = "<table border='1' cellspacing='0' cellpadding='4'><tr><th>Parameter</th>"
    for d in dates:
        html += f"<th>{d}</th>"
    html += "</tr>"
    
    for p in params:
        html += f"<tr><td>{p['parameter_name']}"
        if p.get('unit'):
            html += f"<br>Unit: {p['unit']}"
        if p.get('normalvalue'):
            html += f"<br>Normal: {p['normalvalue']}"
        html += "</td>"
        for val in p.get('result_value', []):
            html += f"<td>{val}</td>"
        html += "</tr>"
    
    html += "</table>"
    return html


@pdfreport_bp.route('/<int:id>', methods=['POST'])
def generate_pdf_report(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Counter
        cursor.execute("SELECT pt_id, reff_by, remarks, sample, total_fee, paid, discount FROM counter WHERE id=%s", (id,))
        counter = cursor.fetchone()
        if not counter:
            return jsonify({"status":404,"message":"Counter not found"}),404

        patient_id = counter['pt_id']
        remarks = counter.get('remarks') or "-"
        sample = counter.get('sample') or "-"
        total_fee_db = counter.get('total_fee') or 0
        paid_db = counter.get('paid') or 0
        discount_db = counter.get('discount') or 0

        # Patient
        cursor.execute("SELECT id, patient_name, cell, gender, age, MR_number, mr_number FROM patient_entry WHERE id=%s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"status":404,"message":"Patient not found"}),404
        mr_number = patient.get('MR_number') or patient.get('mr_number') or ""

        # Referred by
        reff_by_name = "N/A"
        if counter.get('reff_by'):
            cursor.execute("SELECT name FROM users WHERE id=%s", (counter['reff_by'],))
            r = cursor.fetchone()
            if r: reff_by_name = r.get('name') or "N/A"

        # Tests
        data = request.get_json() or {}
        tests_input = data.get("test", [])
        test_ids = [t.get("id") for t in tests_input if t.get("id")]

        if not test_ids:
            cursor.execute("""
                SELECT pt.id AS patient_test_id, pt.verified_by, pt.verified_at, tp.id AS test_id, tp.test_name, tp.interpretation, tp.department_id, tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id=tp.id
                WHERE pt.patient_id=%s AND pt.counter_id=%s
            """, (patient_id, id))
        else:
            placeholders = ",".join(["%s"]*len(test_ids))
            cursor.execute(f"""
                SELECT pt.id AS patient_test_id, pt.verified_by, pt.verified_at, tp.id AS test_id, tp.test_name, tp.interpretation, tp.department_id, tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id=tp.id
                WHERE pt.patient_id=%s AND pt.counter_id=%s AND tp.id IN ({placeholders})
            """, [patient_id, id]+test_ids)

        tests = cursor.fetchall() or []
        test_list = []
        for t in tests:
            # verified info
            verified_name = "N/A"
            verified_qual = ""
            if t.get('verified_by'):
                cursor.execute("SELECT name, qualification FROM users WHERE id=%s", (t['verified_by'],))
                v = cursor.fetchone()
                if v:
                    verified_name = v.get('name') or "N/A"
                    verified_qual = v.get('qualification') or ""

            # interpretation
            interp_detail = None
            if t.get('interpretation'):
                cursor.execute("SELECT detail FROM interpretations WHERE id=%s", (t['interpretation'],))
                idetail = cursor.fetchone()
                if idetail: interp_detail = idetail.get('detail')

            # comment
            cursor.execute("SELECT comment FROM patient_tests WHERE test_id=%s AND counter_id=%s", (t['test_id'], id))
            com = cursor.fetchone()
            commenttext = com.get('comment') if com else None

            # department
            dept_name = "N/A"
            if t.get('department_id'):
                cursor.execute("SELECT department_name FROM departments WHERE id=%s", (t['department_id'],))
                drow = cursor.fetchone()
                if drow: dept_name = drow.get('department_name') or dept_name

            # parameters
            dates, parameters = build_parameters(cursor, patient_id, id, t['test_id'])
            test_list.append({
                "test_name": t.get('test_name'),
                "fee": t.get('fee',0),
                "department": dept_name,
                "dates": dates,
                "parameters": parameters,
                "comment": commenttext,
                "intr_detail": interp_detail,
                "test_verify_info": [{"name": verified_name, "qualification": verified_qual, "verified_at": str(t.get('verified_at'))}]
            })

        # QR code
        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

        # Build simple HTML
        html = f"<html><body><h2>Lab Report</h2><img src='{qr_data_url}' width='80'/><br>"
        html += f"<b>Patient Name:</b> {patient['patient_name']}<br>"
        html += f"<b>MR Number:</b> {mr_number}<br>"
        html += f"<b>Cell:</b> {patient['cell']}<br>"
        html += f"<b>Gender:</b> {patient['gender']}<br>"
        html += f"<b>Age:</b> {patient['age']}<br>"
        html += f"<b>Referred By:</b> {reff_by_name}<br>"
        html += f"<b>Sample:</b> {sample}<br>"
        html += f"<b>Remarks:</b> {remarks}<br><hr>"

        for t in test_list:
            html += f"<h3>{t['department']} - {t['test_name']}</h3>"
            html += render_parameters_html(t)
            if t.get('comment'):
                html += f"<b>Comment:</b> {t['comment']}<br>"
            if t.get('intr_detail'):
                html += f"<b>Interpretation:</b> {t['intr_detail']}<br>"
            vinfo = t.get('test_verify_info', [{}])[0]
            html += f"<b>Verified By:</b> {vinfo.get('name','')} | <b>Qualification:</b> {vinfo.get('qualification','')} | <b>Verified At:</b> {vinfo.get('verified_at','')}<br><hr>"

        unpaid = total_fee_db - paid_db - discount_db
        html += f"<b>Total Fee:</b> {total_fee_db} | <b>Paid:</b> {paid_db} | <b>Discount:</b> {discount_db} | <b>Unpaid:</b> {unpaid}</body></html>"

        # Save PDF
        pdf_filename = f"report_{patient_id}_{int(datetime.now().timestamp())}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
        with open(pdf_path, 'wb') as f:
            pisa_status = pisa.CreatePDF(html, dest=f)
        if pisa_status.err:
            return jsonify({"status":500,"error":"PDF generation failed"}),500

        pdf_url = url_for('pdfreport.get_pdf', filename=pdf_filename, _external=True)
        return jsonify({"status":200,"pdf_url":pdf_url}),200

    except Exception as e:
        return jsonify({"status":500,"error":str(e),"trace":traceback.format_exc()}),500


@pdfreport_bp.route('/file/<filename>', methods=['GET'])
def get_pdf(filename):
    pdf_path = os.path.join(PDF_FOLDER, filename)
    if not os.path.exists(pdf_path):
        return jsonify({"status":404,"message":"File not found"}),404
    return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)