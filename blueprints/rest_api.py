from flask import Blueprint, render_template
from flask_restx import Api

rest_api_bp = Blueprint('rest_api', __name__)

@rest_api_bp.route('/')
def index():
  return 'rest api root'

api = Api(rest_api_bp, doc=False)

