from flask import Flask, jsonify, request, make_response
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import os
from routes.department.department import department_bp
from routes.consultant.consultant import consultant_bp

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
# Add CORS headers to every response
@app.after_request
def add_cors_headers(response):
    # For dev you can keep '*' or replace with specific origin like 'http://localhost:3000'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Respond to preflight OPTIONS early
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


@app.route("/")
def first():
    return jsonify({"message": "Gardezi Lab Backend Api"})


# Register Blueprints
app.register_blueprint(department_bp)
app.register_blueprint(consultant_bp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
