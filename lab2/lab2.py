import os

from dotenv import load_dotenv
from flask import Flask, Blueprint, request
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime

load_dotenv()

db = SQLAlchemy()

queries = Blueprint('queries',__name__)


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price_mdl = db.Column(db.Float, nullable=False)
    price_eur = db.Column(db.Float, nullable=False)
    link = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'


def create_app():
    app = Flask(__name__)
    app.config[
        'SQLALCHEMY_DATABASE_URI'] = f'postgresql://{os.environ.get("POSTGRES_USERNAME")}:{os.environ.get("POSTGRES_PASSWORD")}@{os.environ.get("POSTGRES_URL")}/{os.environ.get("POSTGRES_DATABASE")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.register_blueprint(queries, url_prefix='/')

    with app.app_context():
        db.create_all()

    return app


@queries.route('/product', methods=['POST'])
def create_product():
    data = request.get_json()
    new_product = Product(
        name=data['name'],
        weight=float(data['weight']),
        price_mdl=float(data['price_mdl']),
        price_eur=float(data['price_eur']),
        link=data['link']
    )
    db.session.add(new_product)
    db.session.commit()
    return {"message": "Product added successfully"}, 201


@queries.route('/product', methods=['GET'])
def get_products():
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=5, type=int)
    products = Product.query.offset(offset).limit(limit).all()
    result = []
    for product in products:
        result.append({
            'id': product.id,
            'name': product.name,
            'weight': product.weight,
            'price_mdl': product.price_mdl,
            'price_eur': product.price_eur,
            'link': product.link
        })
    return {"products": result}, 200


@queries.route('/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    product.name = data.get('name', product.name)
    product.weight = float(data.get('weight', product.weight)) if 'weight' in data else product.weight
    product.price_mdl = float(data.get('price_mdl', product.price_mdl)) if 'price_mdl' in data else product.price_mdl
    product.price_eur = float(data.get('price_eur', product.price_eur)) if 'price_eur' in data else product.price_eur
    product.link = data.get('link', product.link)

    db.session.commit()
    return {"message": "Product updated successfully"}, 200


@queries.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return {"message": "Product deleted successfully"}, 200


# route to handle form-data uploads
@queries.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {"message": "no file part in the request"}, 400

    file = request.files['file']
    if file.filename == '':
        return {"message": "no file selected for uploading"}, 400

    if file and file.filename.endswith('.json'):
        file_path = os.path.join('/tmp', file.filename)
        file.save(file_path)

        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                return {"message": "file uploaded and processed successfully", "data": data}, 201
            except json.JSONDecodeError:
                return {"message": "Invalid JSON file"}, 400
    else:
        return {"message": "only JSON files are allowed!!11!"}, 400


app = create_app()

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
