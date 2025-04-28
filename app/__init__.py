from flask import Flask
import os
from dotenv import load_dotenv

def create_app():
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env.test"))

    app = Flask(__name__, template_folder=TEMPLATE_DIR)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    from app.routes import main
    app.register_blueprint(main)

    from pymongo import MongoClient
    from minio import Minio

    app.mongo_db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))[
        os.getenv("MONGO_DBNAME", "dropit")
    ]

    app.minio_client = Minio(
        os.getenv("MINIO_URL", "localhost:9000").replace("http://", ""),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minio_access_key"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minio_secret_key"),
        secure=False,
    )
    app.bucket_name = os.getenv("MINIO_BUCKET_NAME", "dropit-storage")

    return app

