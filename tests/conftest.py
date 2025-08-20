import pytest
from app import create_app
from models import db

@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,                 # disables CSRF check in our code if you want, but we kept it enabled
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture()
def client(app):
    return app.test_client()
