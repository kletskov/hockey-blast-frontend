from flask_restx import Namespace, Resource, fields
from hockey_blast_common_lib.models import Season, db

seasons_ns = Namespace("seasons", description="Seasons at an organization")

season_model = seasons_ns.model(
    "Season",
    {
        "id": fields.Integer(readonly=True, required=True),
        "season_number": fields.Integer(required=True),
        "season_name": fields.String(required=True),
        "start_date": fields.Date(required=True),
        "end_date": fields.Date(required=True),
        "league_number": fields.Integer(required=True),
        "league_id": fields.Integer(required=True),
        "org_id": fields.Integer(required=True),
    },
)

season_list_model = seasons_ns.model(
    "SeasonList",
    {
        "seasons": fields.List(fields.Nested(season_model)),
    },
)


@seasons_ns.route("/organizations/<int:organization_id>/seasons")
@seasons_ns.param("organization_id", "The organization identifier")
class ListSeason(Resource):
    @seasons_ns.marshal_with(season_list_model)
    def get(self, organization_id):
        """List all seasons within an organization"""
        seasons = db.session.query(Season).where(Season.org_id == organization_id)
        return {"seasons": seasons}


@seasons_ns.route("/organizations/<int:organization_id>/seasons/<int:season_id>")
@seasons_ns.response(404, "Season not found")
@seasons_ns.param("organization_id", "The organization identifier")
@seasons_ns.param("season_id", "The season identifier")
class GetSeason(Resource):
    @seasons_ns.marshal_with(season_model)
    def get(self, organization_id, season_id):
        """Get a season by ID"""
        season = db.session.query(Season).get(season_id)

        if not season or season.org_id != organization_id:
            seasons_ns.abort(404, "Season not found")

        return season
