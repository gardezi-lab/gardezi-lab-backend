# pdfreport.py
from flask import Blueprint, request, url_for, jsonify, send_file, current_app
from flask_mysqldb import MySQL
import qrcode
from io import BytesIO
from datetime import datetime
import MySQLdb.cursors
from xhtml2pdf import pisa
import os
import base64
import traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

pdfreport_bp = Blueprint('pdfreport', __name__, url_prefix='/api/pdfreport')
mysql = MySQL()
PDF_FOLDER = 'generated_reports'
os.makedirs(PDF_FOLDER, exist_ok=True)


def build_parameters(cursor, patient_id, counter_id, test_id):
    """
    Build parameter data: one result per parameter per date from patient_results
    """
    cursor.execute("""
        SELECT pr.created_at AS result_date, p.parameter_name, p.unit, p.normalvalue,
               pr.result_value, pr.cutoff_value, p.sub_heading
        FROM patient_results pr
        JOIN parameters p ON pr.parameter_id = p.id
        JOIN patient_tests pt ON pt.patient_id=%s AND pt.counter_id <= %s AND pt.test_id=%s
            AND pt.test_id = p.test_profile_id
        WHERE pr.counter_id = pt.counter_id
        ORDER BY pr.created_at ASC
    """, (patient_id, counter_id, test_id))

    rows = cursor.fetchall() or []

    # unique dates from patient_results
    dates = sorted(list({str(r['result_date'])[:10] for r in rows}))

    params_map = {}
    for r in rows:
        pname = r['parameter_name']
        date_key = str(r['result_date'])[:10]  # just date part
        if pname not in params_map:
            params_map[pname] = {
                "unit": r.get('unit'),
                "normalvalue": r.get('normalvalue'),
                "sub_heading": r.get('sub_heading'),
                "results": {},   # key: date -> result
                "cutoffs": {}
            }
        # overwrite if multiple results: latest will be kept
        params_map[pname]["results"][date_key] = r.get('result_value', '-')
        params_map[pname]["cutoffs"][date_key] = r.get('cutoff_value', '-')

    parameters = []
    for pname, pdata in params_map.items():
        results_list = [pdata["results"].get(d, "-") for d in dates]
        cutoffs = [pdata["cutoffs"].get(d, "-") for d in dates]
        parameters.append({
            "parameter_name": pname,
            "unit": pdata.get("unit"),
            "normalvalue": pdata.get("normalvalue"),
            "sub_heading": pdata.get("sub_heading"),
            "result_value": results_list,
            "cutoff_value": cutoffs
        })

    return dates, parameters

def generate_graph_image(dates, values, parameter_name):
    """
    Generate graph showing results over dates as a line plot.
    """
    y = []
    for v in values:
        try:
            y.append(float(v))  # single value per date
        except:
            y.append(np.nan)

    x_labels = [str(d) for d in dates]
    x = list(range(len(x_labels)))

    fig, ax = plt.subplots(figsize=(4,1.5), dpi=100)
    ax.plot(x, y, marker='o', linewidth=1, markersize=3, color='blue')
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=6)
    ax.tick_params(axis='y', labelsize=7)
    ax.grid(axis='y', linestyle=':', linewidth=0.5)
    plt.tight_layout(pad=0.2)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def render_parameters_html(test):
    """
    Render table with Dates as columns, one result per date, plus graph
    """
    params = test.get('parameters', [])
    if not params:
        return "<p>No parameters available</p>"

    dates = test.get('dates', [])
    html = "<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse; width:100%;'>"
    html += "<tr><th>Parameter</th>"
    for d in dates:
        html += f"<th>{d}</th>"
    html += "<th>Graph</th></tr>"

    for p in params:
        html += f"<tr><td>{p['parameter_name']}</td>"
        for val in p.get('result_value', []):
            html += f"<td style='text-align:center'>{val}</td>"
        graph_img = generate_graph_image(dates, p.get('result_value', []), p['parameter_name'])
        if graph_img:
            html += f"<td><img src='{graph_img}' style='width:240px; height:140px; display:block; margin:auto; object-fit:contain;'></td>"
        else:
            html += "<td>-</td>"
        html += "</tr>"
    html += "</table><br>"
    return html

@pdfreport_bp.route('/<int:id>', methods=['POST'])
def generate_pdf_report(id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT pt_id, reff_by, remarks, sample, total_fee, paid, discount, date_created FROM counter WHERE id=%s", (id,))
        counter = cursor.fetchone()
        if not counter:
            return jsonify({"status":404,"message":"Counter not found"}),404

        patient_id = counter['pt_id']
        remarks = counter.get('remarks') or "-"
        sample = counter.get('sample') or "-"

        cursor.execute("SELECT id, patient_name, cell, gender, age, father_hasband_MR, mr_number, address FROM patient_entry WHERE id=%s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"status":404,"message":"Patient not found"}),404
        mr_number = patient.get('MR_number') or patient.get('mr_number') or ""

        reff_by_name = "N/A"
        if counter.get('reff_by'):
            cursor.execute("SELECT name FROM users WHERE id=%s", (counter['reff_by'],))
            r = cursor.fetchone()
            if r:
                reff_by_name = r.get('name') or "N/A"

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
            verified_name, verified_qual = "N/A", ""
            if t.get('verified_by'):
                cursor.execute("SELECT name, qualification FROM users WHERE id=%s", (t['verified_by'],))
                v = cursor.fetchone()
                if v:
                    verified_name = v.get('name') or "N/A"
                    verified_qual = v.get('qualification') or ""

            interp_detail = None
            if t.get('interpretation'):
                cursor.execute("SELECT detail FROM interpretations WHERE id=%s", (t['interpretation'],))
                idetail = cursor.fetchone()
                if idetail: interp_detail = idetail.get('detail')

            cursor.execute("SELECT comment FROM patient_tests WHERE test_id=%s AND counter_id=%s", (t['test_id'], id))
            com = cursor.fetchone()
            commenttext = com.get('comment') if com else None

            dept_name = "N/A"
            if t.get('department_id'):
                cursor.execute("SELECT department_name FROM departments WHERE id=%s", (t['department_id'],))
                drow = cursor.fetchone()
                if drow: dept_name = drow.get('department_name') or dept_name

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

        qr_text = f"Invoice for {patient['patient_name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

        html = f"""
<html>
<body style="font-family: Arial; font-size: 13px; color: #000;">
<table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">
<tr>
    <td style="width:50%; text-align:left;">
        <img src='./static/gardezi_logo.jpg' alt='Logo' style='width:80px;'>
    </td>
    <td style="width:50%; text-align:right;">
        <img src='{qr_data_url}' alt='QR Code' style='width:80px;'>
    </td>
</tr>
</table>
<table style="width:100%; border-collapse: collapse; margin-bottom:20px;">
<tr>
    <td style="vertical-align: top; width:50%;">
        <table style="width:100%;">
            <tr><td style='font-weight:bold; width:150px;'>Name:</td><td>{patient['patient_name']}</td></tr>
            <tr><td style='font-weight:bold;'>Gender:</td><td>{patient['gender']}</td></tr>
            <tr><td style='font-weight:bold;'>MR No:</td><td>{mr_number}</td></tr>
            <tr><td style='font-weight:bold;'>Phone:</td><td>{patient.get('cell', '')}</td></tr>
            <tr><td style='font-weight:bold;'>Address:</td><td>{patient.get('address', 'N/A')}</td></tr>
        </table>
    </td>
    <td style="vertical-align: top; width:50%;">
        <table style="width:100%;">
            <tr><td style='font-weight:bold; width:180px;'>Father/Husband:</td><td>{patient.get('father_hasband_MR','')}</td></tr>
            <tr><td style='font-weight:bold;'>Registration Date:</td><td>{counter.get('date_created','')}</td></tr>
            <tr><td style='font-weight:bold;'>Date:</td><td>{datetime.now().strftime('%Y-%m-%d')}</td></tr>
            <tr><td style='font-weight:bold;'>Sample Taken In Lab:</td><td>{sample}</td></tr>
            <tr><td style='font-weight:bold;'>Remarks:</td><td>{remarks}</td></tr>
        </table>
    </td>
</tr>
</table>
"""

        for t in test_list:
            html += f"""
<div style="margin-top:10px; margin-bottom:10px;display:flex;  justify-content:space-between;">
    <p style="font-weight:bold; text-align:center; border:0.5px solid black; padding-top:3px; font-size:16px;">
        {t['department']}
    </p>
</div>
<div>
    <p>{t['test_name']}</p>
</div>
"""
            html += render_parameters_html(t)
            if t.get('comment'):
                html += f"<b>Comment:</b> {t['comment']}<br>"
            if t.get('intr_detail'):
                html += f"<b>Interpretation:</b> {t['intr_detail']}<br>"
            vinfo = t.get('test_verify_info', [{}])[0]
            html += f"<b>Verified By:</b> {vinfo.get('name','')} | <b>Qualification:</b> {vinfo.get('qualification','')} | <b>Verified At:</b> {vinfo.get('verified_at','')}<br><hr>"

            footer_path = os.path.join(current_app.root_path, "static", "report_footer.jpeg")
            with open(footer_path, "rb") as f:
                footer_data = base64.b64encode(f.read()).decode()
            html += f"""
<p style='text-align:center;'>
<img src="data:image/jpeg;base64,{footer_data}" style="width:100%; height:110px;">
</p>
"""

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
