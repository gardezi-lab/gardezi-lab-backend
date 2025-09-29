from flask import Flask, jsonify, request, make_response
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import os

# Import blueprints (only once)
from routes.department.department import department_bp
from routes.consultant.consultant import consultant_bp
from routes.parameter.parameter import parameter_bp
from routes.interpretations.interpretations import interpretation_bp
from routes.testpackage.testpackage import packages_bp


from routes.user.users import users_bp 
from routes.companies_panel.companies_panel import companies_panel_bp
from routes.role.role import role_bp
from routes.parameter.parameter import parameter_bp
from routes.test_profile.test_profile import test_profile_bp


# Load .env variables
load_dotenv()
app = Flask(__name__)

# Accept both with / without trailing slash (prevents 308 redirects)
app.url_map.strict_slashes = False

# ---------- MySQL Config ----------
try:
    app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', '127.0.0.1')
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', '')
    app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))

    mysql = MySQL(app)
    app.mysql = mysql
    print("✅ MySQL config loaded successfully:", app.config['MYSQL_HOST'], app.config['MYSQL_DB'])
except Exception as e:
    print("❌ MySQL config failed:", str(e))


# ---------- Manual CORS (Werkzeug / Flask) ----------
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.status_code = 200
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        return resp


# Root test route
@app.route("/")
def first():
    return jsonify({"message": "Gardezi Lab Backend Api"})


# ---------- Register Blueprints ----------
app.register_blueprint(department_bp)
app.register_blueprint(consultant_bp)
app.register_blueprint(parameter_bp)
app.register_blueprint(interpretation_bp)
app.register_blueprint(packages_bp)
app.register_blueprint(users_bp)
app.register_blueprint(companies_panel_bp)
app.register_blueprint(role_bp)
app.register_blueprint(parameter_bp)
app.register_blueprint(test_profile_bp)






# ---------- Run App ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
