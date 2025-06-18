from flask import Blueprint
from flask_restx import Api

# Import all namespaces from api/v1
from api.v1.organizations import organizations_ns
from api.v1.divisions import divisions_ns
from api.v1.seasons import seasons_ns

rest_api_bp = Blueprint('rest_api', __name__)

@rest_api_bp.route('/')
def index():
  return 'rest api root'

# Attach a fully-featured Api object to this blueprint and
# register the imported namespaces under the common prefix.
api = Api(
    rest_api_bp,
    version='1.0',
    title='Hockey BLAST API',
    description='RESTful API',
    doc='/swagger'  # Swagger UI served at /swagger relative to blueprint
)

# Register namespaces
api.add_namespace(organizations_ns, path='/api/v1')
api.add_namespace(divisions_ns, path='/api/v1')
api.add_namespace(seasons_ns, path='/api/v1')
