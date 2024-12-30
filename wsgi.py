from flask_migrate import Migrate
from app import create_app # import db and migrate
from options import orgs
from hockey_blast_common_lib.models import db
org = 'caha'
app = create_app(org, orgs[org])  # Create one app for the migrations
migrate = Migrate(app, db)

# Export db and migrate for flask cli
