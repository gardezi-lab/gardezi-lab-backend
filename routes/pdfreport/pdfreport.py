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

    dates = sorted(list({str(r['result_date'])[:10] for r in rows}))
    params_map = {}
    for r in rows:
        pname = r['parameter_name']
        date_key = str(r['result_date'])[:10]
        if pname not in params_map:
            params_map[pname] = {
                "unit": r.get('unit'),
                "normalvalue": r.get('normalvalue'),
                "sub_heading": r.get('sub_heading'),
                "results": {},
                "cutoffs": {}
            }
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
    y = []
    for v in values:
        try:
            y.append(float(v))
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
        html += f"<td><img src='{graph_img}' style='width:240px; height:140px; display:block; margin:auto; object-fit:contain;'></td>"
        html += "</tr>"
    html += "</table><br>"
    return html


def generate_pdf_html(patient, counter, test_list, qr_data_url="", footer_data="", show_header_footer=True):

    # ------------------ FOOTER ------------------
    footer_block = ""
    if show_header_footer and footer_data:
        footer_block = f"""
        <div id="footer_content" style="text-align:center;">
            <img src="data:image/jpeg;base64,{footer_data}"
                style="width:100%; height:100px;">
        </div>
        """

    # ------------------ HEADER ------------------
    header_block = ""
    if show_header_footer:
        logo_html = "<img src='./static/gardezi_logo.jpg' style='width:70px;'>"
        qr_html = f"<img src='{qr_data_url}' style='width:70px;'>"

        header_block = f"""
        <div id="header_content">
            <table style="width:100%; margin-bottom:5px;">
                <tr>
                    <td style="text-align:left;">{logo_html}</td>
                    <td style="text-align:right;">{qr_html}</td>
                </tr>
            </table>
            <hr style="border:1px solid #000; margin:5px 0;">
        </div>
        """

    # ------------------ PATIENT INFO (ALWAYS REPEAT) ------------------
    patient_info_block = f"""
    <div id="patient_info" style="font-size:12px; width:100%;">

    <table style="width:100%; border-collapse:collapse;">
        <tr>
            <td><b>Name:</b> {patient.get('patient_name','')}</td>
            <td><b>Gender:</b> {patient.get('gender','')}</td>
            <td><b>MR No:</b> {patient.get('mr_number','')}</td>
        </tr>

        <tr>
            <td><b>Phone:</b> {patient.get('cell','')}</td>
            <td><b>Address:</b> {patient.get('address','')}</td>
            <td><b>Father/Husband:</b> {patient.get('guardian_name','')}</td>
        </tr>

        <tr>
            <td><b>Registration:</b> {counter.get('date_created','')}</td>
            <td><b>Date:</b> {counter.get('report_date','')}</td>
            <td><b>Sample:</b> {counter.get('sample','')}</td>
        </tr>

        <tr>
            <td colspan="3"><b>Remarks:</b> {counter.get('remarks','')}</td>
        </tr>
    </table>

</div>
    """

    # ------------------ HTML START ------------------
    html = f"""
<html>
<head>
<style>

@page {{
    margin: 200px 40px 130px 40px;

    /* HEADER FRAME */
    @frame header_frame {{
        -pdf-frame-content: header_content;
        left: 40px;
        right: 40px;
        top: 20px;
        height: 100px;
    }}

    /* PATIENT INFO FRAME (ALWAYS REPEAT) */
    @frame patient_frame {{
        -pdf-frame-content: patient_info;
        left: 40px;
        right: 40px;
        top: 130px;
        height: 90px;
    }}

    /* FOOTER FRAME */
    @frame footer_frame {{
        -pdf-frame-content: footer_content;
        left: 30px;
        right: 30px;
        bottom: 10px;
        height: 110px;
    }}
}}

#header_content, #footer_content, #patient_info {{
    width: 100%;
    position: relative;
}}

body {{
    font-family: Arial;
    font-size: 13px;
    color: #000;
}}

</style>
</head>

<body>

{header_block}
{patient_info_block}
{footer_block}

<!-- BODY CONTENT START (NO PATIENT INFO HERE ANYMORE) -->
"""

    # ------------------ TESTS LOOP ------------------
    for t in test_list:

        html += f"""
        <div style="border:1px solid #000; padding:5px; width:fit-content; margin:5px auto; text-align:center;">
            <b>{t.get('department','')}</b>
        </div>

        <div style="margin-bottom:8px;">
            {t.get('test_name','')}
        </div>
        """

        html += render_parameters_html(t)

        if t.get('comment'):
            html += f"<p><b>Comment:</b> {t['comment']}</p>"

        if t.get('intr_detail'):
            html += f"<p><b>Interpretation:</b> {t['intr_detail']}</p>"

        vinfo = t.get("test_verify_info", [{}])[0]

        html += f"""
        <p style="margin-top:5px;">
            <b>Verified By:</b> {vinfo.get('name','')} |
            <b>Qualification:</b> {vinfo.get('qualification','')} |
            <b>Verified At:</b> {vinfo.get('verified_at','')}
        </p>
        """

    html += "</body></html>"
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

        cursor.execute("SELECT id, patient_name, cell, gender, age, father_hasband_MR, mr_number, address FROM patient_entry WHERE id=%s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"status":404,"message":"Patient not found"}),404

        data = request.get_json() or {}
        tests_input = data.get("test", [])
        test_ids = [t.get("id") for t in tests_input if t.get("id")]
        show_header_footer = data.get("show_header_footer", True)

        placeholders = ",".join(["%s"]*len(test_ids)) if test_ids else None
        if placeholders:
            cursor.execute(f"""
                SELECT pt.id AS patient_test_id, pt.verified_by, pt.verified_at, tp.id AS test_id, tp.test_name, tp.interpretation, tp.department_id, tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id=tp.id
                WHERE pt.patient_id=%s AND pt.counter_id=%s AND tp.id IN ({placeholders})
            """, [patient_id, id]+test_ids)
        else:
            cursor.execute(f"""
                SELECT pt.id AS patient_test_id, pt.verified_by, pt.verified_at, tp.id AS test_id, tp.test_name, tp.interpretation, tp.department_id, tp.fee
                FROM patient_tests pt
                JOIN test_profiles tp ON pt.test_id=tp.id
                WHERE pt.patient_id=%s AND pt.counter_id=%s
            """, (patient_id, id))

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
        footer_path = os.path.join(current_app.root_path, "static", "report_footer.jpeg")
        with open(footer_path, "rb") as f:
            footer_data = base64.b64encode(f.read()).decode()

        html = generate_pdf_html(
            patient, 
            counter, 
            test_list, 
            qr_data_url=qr_data_url, 
            footer_data=footer_data, 
            show_header_footer=show_header_footer  # single toggle
)


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
