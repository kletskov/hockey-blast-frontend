from flask_restx import Namespace, Resource, fields
from hockey_blast_common_lib.models import Division, db

divisions_ns = Namespace("divisions", description="Divisions within an organization")

division_model = divisions_ns.model(
    "Division",
    {
        "id": fields.Integer(readonly=True, required=True),
        "league_number": fields.Integer(required=True),
        "season_number": fields.Integer(required=True),
        "season_id": fields.Integer(required=True),
        "level": fields.String(required=True),
        "level_id": fields.Integer(required=True),
        "org_id": fields.Integer(required=True),
    },
)

division_list_model = divisions_ns.model(
    "DivisionList",
    {
        "divisions": fields.List(fields.Nested(division_model)),
    },
)


@divisions_ns.route("/organizations/<int:organization_id>/divisions")
@divisions_ns.response(404, "Division not found")
@divisions_ns.param("organization_id", "The organization identifier")
class ListDivisions(Resource):
    @divisions_ns.marshal_with(division_list_model)
    def get(self, organization_id):
        """List all divisions within an organization"""
        divisions = db.session.query(Division).where(Division.org_id == organization_id)
        return {"divisions": divisions}


@divisions_ns.route("/organizations/<int:organization_id>/divisions/<int:division_id>")
@divisions_ns.response(404, "Division not found")
@divisions_ns.param("organization_id", "The organization identifier")
@divisions_ns.param("division_id", "The division identifier")
class GetDivision(Resource):
    @divisions_ns.marshal_with(division_model)
    def get(self, organization_id, division_id):
        """Get a division by ID"""
        division = db.session.query(Division).get(division_id)

        if not division or division.org_id != organization_id:
            divisions_ns.abort(404, "Division not found")

        return division
