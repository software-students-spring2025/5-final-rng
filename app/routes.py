import os
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    flash,
    send_file,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from nanoid import generate
from pymongo import MongoClient
from minio import Minio
import bcrypt

main = Blueprint("main", __name__)
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "dropit_uploads"
)

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client["dropit"]
files_collection = db["files"]

minio = Minio(
    os.getenv("MINIO_URL", "http://localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minio_access_key"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minio_secret_key"),
    secure=False,
)

bucket_name = os.getenv("MINIO_BUCKET_NAME", "dropit-storage")

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


# Modify your upload_file route to hash the password
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
    password = request.form.get("password", "")  # Now optional
    expiration_days = request.form.get("expiration-date", "7")  # Default to 7 days
    download_limit = request.form.get("download-limit", "0")
    description = request.form.get("description", "")

    # Hash the password if one is provided
    hashed_password = hash_password(password) if password else ""

    # If the hashed password is bytes, convert to string for MongoDB storage
    if isinstance(hashed_password, bytes):
        hashed_password = hashed_password.decode("utf-8")

    # Convert download_limit to integer
    try:
        download_limit = int(download_limit) if download_limit else 0
    except ValueError:
        download_limit = 0

    try:
        expiration_days = int(expiration_days)
        expiration_date = (
            datetime.utcnow() + timedelta(days=expiration_days)
        ).strftime("%Y-%m-%d")
    except ValueError:
        expiration_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

    # Save the file with a unique name
    original_filename = file.filename
    saved_name = f"{file_id}_{original_filename}"
    local_path = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(local_path)

    try:
        # upload to the bucket
        # Make the bucket if it doesn't exist.
        found = minio.bucket_exists(bucket_name)
        if not found:
            minio.make_bucket(bucket_name)
            print("Created bucket", bucket_name)
        else:
            print("Bucket", bucket_name, "already exists")

        # Upload the file, renaming it in the process
        minio.fput_object(
            bucket_name,
            saved_name,
            local_path,
        )
        print(
            local_path,
            "successfully uploaded as object",
            saved_name,
            "to bucket",
            bucket_name,
        )

        # Get file information
        file_size = os.path.getsize(local_path)
        content_type = file.content_type
        file_icon = get_file_icon(original_filename, content_type)

        # Save metadata to MongoDB with hashed password
        file_data = {
            "_id": file_id,
            "original_filename": original_filename,
            "saved_filename": saved_name,
            "file_size": file_size,
            "content_type": content_type,
            "file_icon": file_icon,
            "upload_time": datetime.utcnow(),
            "password": hashed_password,  # Store the hashed password
            "has_password": bool(password),  # Store whether a password was set
            "expiration_date": expiration_date,
            "download_limit": download_limit,
            "download_count": 0,
            "description": description,
        }

        files_collection.insert_one(file_data)

        # Delete the local file after successful upload to MinIO and metadata saved to MongoDB
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Local file {local_path} deleted successfully")

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

    except Exception as e:
        # If an error occurs during the process, make sure to clean up the local file
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Local file {local_path} deleted after error")

        # Log the error
        print(f"Error during file upload: {str(e)}")

        # Return an error response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Upload failed. Please try again."}), 500

        flash("Upload failed. Please try again.", "error")
        return redirect(request.url)


@main.route("/files/<file_id>", methods=["GET", "POST"])
def access_file(file_id):
    """Password verification screen and file download handler"""
    file_doc = files_collection.find_one({"_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found or it is expired"}), 404

    # if password is empty
    if not file_doc["has_password"]:
        return render_template("download.html", file=file_doc)
    
    # Handle POST request (from verify.html form)
    if request.method == "POST":
        entered_password = request.form.get("password", None)
        if entered_password and verify_password(file_doc["password"], entered_password):
            return render_template(
                "download.html", file=file_doc, password=entered_password
            )
        else:
            flash("Incorrect password", "error")
            return render_template("verify.html", file_id=file_doc["_id"])

    # Handle GET request
    entered_password = request.args.get("password", None)

    if entered_password:
        if verify_password(file_doc["password"], entered_password):
            return render_template(
                "download.html", file=file_doc, password=entered_password
            )

    # Check if file is expired
    if file_doc.get("expiration_date"):
        try:
            expiration_date = datetime.strptime(file_doc["expiration_date"], "%Y-%m-%d")
            if datetime.utcnow() > expiration_date:
                flash("This file has expired", "error")
                return redirect(url_for("main.index"))
        except ValueError:
            # If date format is invalid, ignore expiration check
            pass

    # Check if download limit is reached
    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        flash("Download limit reached for this file", "error")
        return redirect(url_for("main.index"))

    # GET request - show password verification form if needed
    return render_template(
        "verify.html",
        file_id=file_doc["_id"],
    )


@main.route("/files/<file_id>/download")
def download_file(file_id):
    file_doc = files_collection.find_one({"_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found or it is expired"}), 404

    entered_password = request.args.get("password")

    # Check if password is required and verify it
    if file_doc["has_password"]:
        if not entered_password or not verify_password(
            file_doc["password"], entered_password
        ):
            return redirect(url_for("main.access_file", file_id=file_id))

    # Check if file is expired
    if file_doc.get("expiration_date"):
        try:
            expiration_date = datetime.strptime(file_doc["expiration_date"], "%Y-%m-%d")
            if datetime.utcnow() > expiration_date:
                flash("This file has expired", "error")
                return redirect(url_for("main.index"))
        except ValueError:
            # If date format is invalid, ignore expiration check
            pass

    # Check if download limit is reached
    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        flash("Download limit reached for this file", "error")
        return redirect(url_for("main.index"))

    # Create a temporary file to store the downloaded content
    temp_file_path = os.path.join(
        UPLOAD_FOLDER, os.path.basename(file_doc["saved_filename"])
    )

    try:
        # Ensure the upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Get the file from MinIO
        minio.fget_object(bucket_name, file_doc["saved_filename"], temp_file_path)

        # Update download count
        files_collection.update_one({"_id": file_id}, {"$inc": {"download_count": 1}})

        # Serve the file to the user
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
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


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
        download_url=url_for(
            "main.access_file", file_id=file_doc["_id"], _external=True
        ),
    )


# Add these functions after your imports but before your routes
def hash_password(password):
    """
    Hash a password using bcrypt

    Args:
        password (str): The plain text password

    Returns:
        bytes: The hashed password
    """
    if not password:
        return None

    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

    return hashed


def verify_password(stored_hash, provided_password):
    """
    Verify a password against a stored hash

    Args:
        stored_hash (bytes or str): The hashed password from the database
        provided_password (str): The plain text password to check

    Returns:
        bool: True if the password matches, False otherwise
    """
    # If no password was set, and none provided, return True
    if not stored_hash:
        return not provided_password

    # If stored_hash is a string (from MongoDB), convert it to bytes
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    # Check if the provided password matches the stored hash
    return bcrypt.checkpw(provided_password.encode("utf-8"), stored_hash)
