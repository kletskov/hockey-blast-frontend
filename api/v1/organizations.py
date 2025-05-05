from flask_restx import Namespace, Resource, fields
from hockey_blast_common_lib.models import db, Organization

organizations_ns = Namespace('organizations', description='Hockey organizations')

organization_model = organizations_ns.model('Organization', {
  'id': fields.Integer(readonly=True, description='Primary id'),
  'alias': fields.String(required=True),
  'organization_name': fields.String(required=True),
  'website': fields.String(),
})

organization_list_model = organizations_ns.model('OrganizationList', {
  'organizations': fields.List(fields.Nested(organization_model)),
})

@organizations_ns.route('/')
class ListOrganizations(Resource):
  @organizations_ns.doc('list_organizations')
  @organizations_ns.marshal_with(organization_list_model)
  def get(self):
    """List all organizations"""
    organizations = db.session.query(Organization).all()
    return {'organizations': organizations}

@organizations_ns.route('/<int:id>')
@organizations_ns.response(404, 'Organization not found')
@organizations_ns.param('id', 'The organization identifier')
class GetOrganization(Resource):
  @organizations_ns.doc('get_organization')
  @organizations_ns.marshal_with(organization_model)
  def get(self, id):
    """Fetch an organization given its identifier"""
    organization = db.session.query(Organization).get(id)
    if not organization:
      organizations_ns.abort(404, 'Organization not found')
    return organization
