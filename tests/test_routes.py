import os
import tempfile
import pytest
import mongomock
import bcrypt
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from dotenv import load_dotenv
from app import create_app

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env.test"))

@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    app.mongo_db = mongomock.MongoClient().db
    app.minio_client = MagicMock()
    app.bucket_name = "dropit-storage"
    with app.app_context():
        yield app

@pytest.fixture
def app_client(app):
    return app.test_client()

@pytest.fixture
def mongo_collection(app):
    collection = app.mongo_db["files"]
    collection.delete_many({})

    hashed_pw = bcrypt.hashpw("testpassword".encode(), bcrypt.gensalt()).decode()

    collection.insert_many([
        {
            "_id": "test_no_password",
            "original_filename": "nopassword.txt",
            "saved_filename": "nopassword_saved.txt",
            "file_size": 1000,
            "content_type": "text/plain",
            "file_icon": "fa-file",
            "upload_time": datetime.now(timezone.utc),
            "password": "",
            "has_password": False,
            "expiration_date": None,
            "download_limit": 0,
            "download_count": 0,
            "description": "no password file"
        },
        {
            "_id": "test_with_password",
            "original_filename": "withpassword.txt",
            "saved_filename": "withpassword_saved.txt",
            "file_size": 1200,
            "content_type": "text/plain",
            "file_icon": "fa-file",
            "upload_time": datetime.now(timezone.utc),
            "password": hashed_pw,
            "has_password": True,
            "expiration_date": None,
            "download_limit": 5,
            "download_count": 0,
            "description": "password protected file"
        },
        {
            "_id": "test_expired_file",
            "original_filename": "expiredfile.txt",
            "saved_filename": "expiredfile_saved.txt",
            "file_size": 800,
            "content_type": "text/plain",
            "file_icon": "fa-file",
            "upload_time": datetime.now(timezone.utc),
            "password": "",
            "has_password": False,
            "expiration_date": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
            "download_limit": 0,
            "download_count": 0,
            "description": "expired test file"
        },
        {
            "_id": "test_download_limit_exceeded",
            "original_filename": "limitfile.txt",
            "saved_filename": "limitfile_saved.txt",
            "file_size": 500,
            "content_type": "text/plain",
            "file_icon": "fa-file",
            "upload_time": datetime.now(timezone.utc),
            "password": "",
            "has_password": False,
            "expiration_date": None,
            "download_limit": 1,
            "download_count": 1,
            "description": "limit exceeded file"
        }
    ])

    yield collection
    collection.delete_many({})

# ---------------- 基础功能测试 ----------------

def test_homepage_loads(app_client):
    response = app_client.get("/")
    assert response.status_code == 200
    assert b'Upload' in response.data

def test_file_upload_success(app_client):
    with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
        temp.write(b'Test content')
        temp.seek(0)
        data = {
            "file": (temp, "testfile.txt"),
            "password": "mypassword",
            "expiration-date": "1",
            "download-limit": "3",
            "description": "Test upload"
        }
        response = app_client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    assert b'Success' in response.data or b'File' in response.data

def test_access_nonexistent_file(app_client):
    response = app_client.get("/files/nonexistentfile")
    assert response.status_code == 404

def test_password_verification_success(app_client, mongo_collection):
    response = app_client.post(
        "/files/test_with_password",
        data={"password": "testpassword"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'Download' in response.data or b'File' in response.data

def test_password_verification_failure(app_client, mongo_collection):
    response = app_client.post(
        "/files/test_with_password",
        data={"password": "wrongpassword"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'Incorrect password' in response.data

def test_file_download_flow(app_client, mongo_collection):
    response = app_client.get(
        "/files/test_with_password/download?password=testpassword",
        follow_redirects=True
    )
    assert response.status_code == 200

# ---------------- 边界测试 ----------------

def test_upload_with_invalid_expiration(app_client):
    with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
        temp.write(b'Sample data')
        temp.seek(0)
        data = {
            "file": (temp, "testfile_invalid_exp.txt"),
            "expiration-date": "invalid"
        }
        response = app_client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    assert b'Success' in response.data or b'File' in response.data

def test_upload_without_download_limit(app_client):
    with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
        temp.write(b'Sample file')
        temp.seek(0)
        data = {
            "file": (temp, "testfile_nolimit.txt"),
            "expiration-date": "5"
        }
        response = app_client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200

def test_access_expired_file(app_client, mongo_collection):
    response = app_client.get("/files/test_expired_file", follow_redirects=True)
    assert response.status_code == 200
    assert b'This file has expired' in response.data

def test_download_limit_exceeded(app_client, mongo_collection):
    response = app_client.get("/files/test_download_limit_exceeded", follow_redirects=True)
    assert response.status_code == 200
    assert b'Download limit reached' in response.data



