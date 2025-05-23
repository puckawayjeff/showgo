# showgo/extensions.py
# Initialize Flask extensions here to avoid circular imports

from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth

db = SQLAlchemy()
auth = HTTPBasicAuth(realm="ShowGo Configuration Access")

