from flask import Flask,jsonify
from flask_mysqldb import MySQL
from routes.department.department import department_bp
from routes.consultant.consultent import consultant_bp

app = Flask(__name__)



mysql = MySQL(app)
app.mysql = mysql

@app.route("/")
def first():
    return jsonify({"message": "Gardezi Lab Backend Api"})

app.register_blueprint(department_bp)
app.register_blueprint(consultant_bp)

if __name__ == '__main__':
    app.run(debug=True)