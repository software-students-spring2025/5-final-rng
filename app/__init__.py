from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    template_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(template_dir, "templates")

    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    from app.routes import main

    app.register_blueprint(main)

    return app
