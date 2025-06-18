import os
from functools import wraps
from flask import Blueprint, request, abort, current_app
from flask_restx import Api

# Import all namespaces from api/v1
from api.v1.organizations import organizations_ns
from api.v1.divisions import divisions_ns
from api.v1.seasons import seasons_ns

rest_api_bp = Blueprint('rest_api', __name__)

@rest_api_bp.route('/')
def index():
  return 'rest api root'

# ------------------------------------------------------------------------------
# API-key authentication setup
# ------------------------------------------------------------------------------

# Swagger / OpenAPI security scheme
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

def require_api_key(func):
    """
    Simple decorator to enforce an API key on every request handled by this
    blueprint's Api.  Expects the client to send the key in the `X-API-KEY`
    request header.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        # Prefer key from app config, fall back to environment variable
        expected_key = current_app.config.get('API_KEY') or os.environ.get('API_KEY')
        if expected_key and provided_key == expected_key:
            return func(*args, **kwargs)
        abort(401, 'Invalid or missing API key')

    return wrapper

# ------------------------------------------------------------------------------
# Attach a fully-featured Api object to this blueprint and register namespaces
# register the imported namespaces under the common prefix.
api = Api(
    rest_api_bp,
    version='1.0',
    title='Hockey BLAST API',
    description='RESTful API',
    doc='/swagger',  # Swagger UI served at /swagger relative to blueprint
    authorizations=authorizations,
    security='apikey',
    decorators=[require_api_key],  # Enforce auth globally
)

# Register namespaces
api.add_namespace(organizations_ns, path='/api/v1')
api.add_namespace(divisions_ns, path='/api/v1')
api.add_namespace(seasons_ns, path='/api/v1')
