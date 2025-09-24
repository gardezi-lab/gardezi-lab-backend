from flask import Flask, jsonify
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import os
from routes.department.department import department_bp
from routes.consultant.consultant import consultant_bp

# Load .env variables
load_dotenv()

app = Flask(__name__)

# MySQL Config
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))

mysql = MySQL(app)
app.mysql = mysql

@app.route("/")
def first():
    return jsonify({"message": "Gardezi Lab Backend Api"})

# Register Blueprints
app.register_blueprint(department_bp)
app.register_blueprint(consultant_bp)

if __name__ == '__main__':
    app.run(debug=True)
