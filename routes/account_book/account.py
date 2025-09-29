from flask import Blueprint, request, jsonify
from flask_mysqldb import MySQL

account_bp = Blueprint('account', __name__, url_prefix='/api/account')
mysql = MySQL()


@account_bp.route('/', methods=['GET'])
def get_roles():
    try:
        account = "Hello From Account Get Api"                 
        return jsonify(account), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


