import os
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from nanoid import generate
from pymongo import MongoClient

main = Blueprint("main", __name__)
UPLOAD_FOLDER = "uploads"

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client["filesharing"]
files_collection = db["uploads"]

# File type icons mapping
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
    """Determine the appropriate icon based on file type"""
    if content_type and content_type.startswith("image/"):
        return file_type_icons["image"]
    elif content_type and content_type.startswith("video/"):
        return file_type_icons["video"]
    elif content_type and content_type.startswith("audio/"):
        return file_type_icons["audio"]
    elif content_type and content_type.startswith("application/pdf"):
        return file_type_icons["pdf"]

    # Check extensions
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
    """Render file upload form"""
    return render_template("upload_enhanced.html")


@main.route("/", methods=["POST"])
def upload_file():
    """Handle file upload and metadata"""
    # Check if a file was uploaded
    if "file" not in request.files:
        flash("No file selected", "error")
        return redirect(request.url)

    file = request.files["file"]

    # Check if file was selected
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(request.url)

    # Generate a unique ID for the file
    file_id = generate()

    # Get metadata from the form
    password = request.form.get("password", "")
    expiration_date = request.form.get("expiration-date", "")
    download_limit = request.form.get("download-limit", "0")
    description = request.form.get("description", "")

    # Convert download_limit to integer
    try:
        download_limit = int(download_limit) if download_limit else 0
    except ValueError:
        download_limit = 0

    # Save the file with a unique name
    original_filename = file.filename
    saved_name = f"{file_id}_{original_filename}"
    local_path = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(local_path)

    # Get file information
    file_size = os.path.getsize(local_path)
    content_type = file.content_type
    file_icon = get_file_icon(original_filename, content_type)

    # Save metadata to MongoDB
    file_data = {
        "_id": file_id,
        "original_filename": original_filename,
        "saved_filename": saved_name,
        "file_path": local_path,
        "file_size": file_size,
        "content_type": content_type,
        "file_icon": file_icon,
        "upload_time": datetime.utcnow(),
        "password": password,
        "expiration_date": expiration_date,
        "download_limit": download_limit,
        "download_count": 0,
        "description": description,
    }

    files_collection.insert_one(file_data)

    # Handle AJAX requests
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "success": True,
                "file_id": file_id,
                "redirect_url": url_for("main.file_success", file_id=file_id),
            }
        )

    return redirect(url_for("main.file_success", file_id=file_id))


@main.route("/files/<file_id>", methods=["GET", "POST"])
def access_file(file_id):
    """Password verification screen and file download handler"""
    file_doc = files_collection.find_one({"_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found"}), 404

    return render_template(
        "verify.html",
        file_id=file_doc["_id"],
        filename=file_doc["original_filename"],
        has_password=bool(file_doc.get("password")),
        download_limit=file_doc.get("download_limit", 0),
        download_count=file_doc.get("download_count", 0),
    )


@main.route("/files/<file_id>/success")
def file_success(file_id):
    file_doc = files_collection.find_one({"_id": file_id})

    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    # Format file size to human readable
    def format_file_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1048576:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1048576:.1f} MB"

    return render_template(
        "success.html",
        file_id=file_doc["_id"],
        file_name=file_doc["original_filename"],
        file_size=format_file_size(file_doc["file_size"]),
        expiration_date=file_doc.get("expiration_date", "Never"),
        download_limit=file_doc.get("download_limit", 0) or "Unlimited",
        download_url=url_for("main.access_file", file_id=file_doc["_id"], _external=True),
    )
