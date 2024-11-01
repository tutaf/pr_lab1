import logging
import os

from dotenv import load_dotenv
from flask import Flask, Blueprint
from flask_sqlalchemy import SQLAlchemy


load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    # app.config['SECRET_KEY'] = f'{os.environ.get("SECRET_KEY")}'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{os.environ.get("POSTGRES_USERNAME")}:{os.environ.get("POSTGRES_PASSWORD")}@{os.environ.get("POSTGRES_URL")}/{os.environ.get("POSTGRES_DATABASE")}'

    db.init_app(app)
    app.register_blueprint(queries, url_prefix='/')

    return app


queries = Blueprint('queries',__name__)



app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
