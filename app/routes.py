import os
from datetime import datetime, timedelta, timezone
from flask import (
    Blueprint,
    flash,
    send_file,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from nanoid import generate
import bcrypt

main = Blueprint("main", __name__)
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "dropit_uploads"
)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

file_type_icons = {
    "image": "fa-file-image",
    "pdf": "fa-file-pdf",
    "word": "fa-file-word",
    "excel": "fa-file-excel",
    "video": "fa-file-video",
    "audio": "fa-file-audio",
    "archive": "fa-file-archive",
    "text": "fa-file-alt",
    "default": "fa-file",
}


def get_file_icon(filename, content_type):
    if content_type and content_type.startswith("image/"):
        return file_type_icons["image"]
    elif content_type and content_type.startswith("video/"):
        return file_type_icons["video"]
    elif content_type and content_type.startswith("audio/"):
        return file_type_icons["audio"]
    elif content_type and content_type.startswith("application/pdf"):
        return file_type_icons["pdf"]

    lowercase_name = filename.lower()
    if lowercase_name.endswith((".doc", ".docx")):
        return file_type_icons["word"]
    elif lowercase_name.endswith((".xls", ".xlsx", ".csv")):
        return file_type_icons["excel"]
    elif lowercase_name.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return file_type_icons["archive"]
    elif lowercase_name.endswith((".txt", ".rtf", ".md")):
        return file_type_icons["text"]

    return file_type_icons["default"]


@main.route("/", methods=["GET"])
def index():
    return render_template("upload_enhanced.html")


@main.route("/", methods=["POST"])
def upload_file():
    files_collection = current_app.mongo_db["files"]
    minio = current_app.minio_client
    bucket_name = current_app.bucket_name

    if "file" not in request.files:
        flash("No file selected", "error")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(request.url)

    file_id = generate()
    password = request.form.get("password", "")
    expiration_days = request.form.get("expiration-date", "7")
    download_limit = request.form.get("download-limit", "0")
    description = request.form.get("description", "")

    hashed_password = hash_password(password) if password else ""
    if isinstance(hashed_password, bytes):
        hashed_password = hashed_password.decode("utf-8")

    try:
        download_limit = int(download_limit) if download_limit else 0
    except ValueError:
        download_limit = 0

    try:
        expiration_days = int(expiration_days)
        # Set expiration to end of day (23:59:59) on the expiration date
        expiration_datetime = datetime.now(timezone.utc) + timedelta(
            days=expiration_days
        )
        expiration_datetime = expiration_datetime.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        expiration_date = expiration_datetime.isoformat()
    except ValueError:
        expiration_datetime = datetime.now(timezone.utc) + timedelta(days=7)
        expiration_datetime = expiration_datetime.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        expiration_date = expiration_datetime.isoformat()

    original_filename = file.filename
    saved_name = f"{file_id}_{original_filename}"
    local_path = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(local_path)

    try:
        found = minio.bucket_exists(bucket_name)
        if not found:
            minio.make_bucket(bucket_name)

        minio.fput_object(bucket_name, saved_name, local_path)

        file_size = os.path.getsize(local_path)
        content_type = file.content_type
        file_icon = get_file_icon(original_filename, content_type)

        file_data = {
            "_id": file_id,
            "original_filename": original_filename,
            "saved_filename": saved_name,
            "file_size": file_size,
            "content_type": content_type,
            "file_icon": file_icon,
            "upload_time": datetime.now(timezone.utc),
            "password": hashed_password,
            "has_password": bool(password),
            "expiration_date": expiration_date,
            "download_limit": download_limit,
            "download_count": 0,
            "description": description,
        }

        files_collection.insert_one(file_data)

        if os.path.exists(local_path):
            os.remove(local_path)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "success": True,
                    "file_id": file_id,
                    "redirect_url": url_for("main.file_success", file_id=file_id),
                }
            )

        return redirect(url_for("main.file_success", file_id=file_id))

    except Exception as e:
        if os.path.exists(local_path):
            os.remove(local_path)
        print(f"Error during file upload: {str(e)}")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Upload failed. Please try again."}), 500

        flash("Upload failed. Please try again.", "error")
        return redirect(request.url)


@main.route("/files/<file_id>", methods=["GET", "POST"])
def access_file(file_id):
    files_collection = current_app.mongo_db["files"]
    file_doc = files_collection.find_one({"_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found or it is expired"}), 404

    if file_doc.get("expiration_date"):
        # Check if we're using the old date format
        if len(file_doc["expiration_date"]) == 10:  # YYYY-MM-DD format
            # Convert to timezone-aware datetime by adding timezone information
            expiration_date = datetime.strptime(
                file_doc["expiration_date"], "%Y-%m-%d"
            ).replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            )
        else:  # Using new ISO format
            expiration_date = datetime.fromisoformat(file_doc["expiration_date"])

        current_date = datetime.now(timezone.utc)
        if current_date > expiration_date:
            return render_template("download.html", file=file_doc, expired=True)

    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        return render_template("download.html", file=file_doc, limit_reached=True)

    if not file_doc["has_password"]:
        return render_template("download.html", file=file_doc)

    if request.method == "POST":
        entered_password = request.form.get("password", None)
        if entered_password and verify_password(file_doc["password"], entered_password):
            return render_template(
                "download.html", file=file_doc, password=entered_password
            )
        else:
            flash("Incorrect password", "error")
            return render_template("verify.html", file_id=file_doc["_id"])

    entered_password = request.args.get("password", None)
    if entered_password and verify_password(file_doc["password"], entered_password):
        return render_template(
            "download.html", file=file_doc, password=entered_password
        )

    return render_template("verify.html", file_id=file_doc["_id"])


@main.route("/files/<file_id>/download")
def download_file(file_id):
    files_collection = current_app.mongo_db["files"]
    minio = current_app.minio_client
    bucket_name = current_app.bucket_name

    file_doc = files_collection.find_one({"_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found or it is expired"}), 404

    # Check if file has expired
    if file_doc.get("expiration_date"):
        # Check if we're using the old date format
        if len(file_doc["expiration_date"]) == 10:  # YYYY-MM-DD format
            # Convert to timezone-aware datetime by adding timezone information
            expiration_date = datetime.strptime(
                file_doc["expiration_date"], "%Y-%m-%d"
            ).replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            )
        else:  # Using new ISO format
            expiration_date = datetime.fromisoformat(file_doc["expiration_date"])

        current_date = datetime.now(timezone.utc)
        if current_date > expiration_date:
            flash("This file has expired", "error")
            return redirect(url_for("main.access_file", file_id=file_id))

    # Check download limits
    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        flash("Download limit reached", "error")
        return redirect(url_for("main.access_file", file_id=file_id))

    entered_password = request.args.get("password")
    if file_doc["has_password"]:
        if not entered_password or not verify_password(
            file_doc["password"], entered_password
        ):
            return redirect(url_for("main.access_file", file_id=file_id))

    temp_file_path = os.path.join(
        UPLOAD_FOLDER, os.path.basename(file_doc["saved_filename"])
    )
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        minio.fget_object(bucket_name, file_doc["saved_filename"], temp_file_path)

        files_collection.update_one({"_id": file_id}, {"$inc": {"download_count": 1}})

        return send_file(
            temp_file_path,
            mimetype=file_doc.get("content_type", "application/octet-stream"),
            as_attachment=True,
            download_name=file_doc["original_filename"],
        )
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        flash("Error downloading file. Please try again.", "error")
        return redirect(url_for("main.index"))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@main.route("/files/<file_id>/success")
def file_success(file_id):
    files_collection = current_app.mongo_db["files"]
    file_doc = files_collection.find_one({"_id": file_id})

    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    def format_file_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1048576:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1048576:.1f} MB"

    # Format expiration date for display
    expiration_display = "Never"
    if file_doc.get("expiration_date"):
        try:
            # Check if we're using the old date format
            if len(file_doc["expiration_date"]) == 10:  # YYYY-MM-DD format
                expiration_date = datetime.strptime(
                    file_doc["expiration_date"], "%Y-%m-%d"
                )
            else:  # Using new ISO format
                expiration_date = datetime.fromisoformat(file_doc["expiration_date"])

            expiration_display = expiration_date.strftime("%b %d, %Y at %I:%M %p")
        except ValueError:
            expiration_display = file_doc.get("expiration_date", "Never")

    return render_template(
        "success.html",
        file_id=file_doc["_id"],
        file_name=file_doc["original_filename"],
        file_size=format_file_size(file_doc["file_size"]),
        expiration_date=expiration_display,
        download_limit=file_doc.get("download_limit", 0) or "Unlimited",
        download_url=url_for(
            "main.access_file", file_id=file_doc["_id"], _external=True
        ),
    )


def hash_password(password):
    if not password:
        return None
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed


def verify_password(stored_hash, provided_password):
    if not stored_hash:
        return not provided_password
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")
    return bcrypt.checkpw(provided_password.encode("utf-8"), stored_hash)
