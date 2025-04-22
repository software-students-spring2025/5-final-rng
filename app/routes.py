# Add/modify these imports at the top if needed
from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    render_template,
    flash,
    send_file,
    jsonify,
)
from pymongo import MongoClient
import os
import uuid
from datetime import datetime

# Replace or modify your existing index route to handle the new upload form
@main.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if a file was uploaded
        if "file" not in request.files:
            flash("No file part", "error")
            return jsonify({"success": False, "message": "No file part"}), 400
        
        uploaded_file = request.files["file"]
        
        # Check if file was selected
        if uploaded_file.filename == "":
            flash("No file selected", "error")
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Generate a unique ID for the file
        file_id = str(uuid.uuid4())
        
        # Get metadata from the form
        password = request.form.get("password", "")
        expiration_date = request.form.get("expiration-date", "")  # Note the hyphen here
        download_limit = request.form.get("download-limit", "0")  # Note the hyphen here
        
        # Convert download_limit to integer
        try:
            download_limit = int(download_limit) if download_limit else 0
        except ValueError:
            download_limit = 0
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # Save the file with a unique name
        saved_name = f"{file_id}_{uploaded_file.filename}"
        local_path = os.path.join(UPLOAD_FOLDER, saved_name)
        uploaded_file.save(local_path)
        
        # Save metadata to MongoDB
        files_collection.insert_one({
            "file_id": file_id,
            "filename": uploaded_file.filename,
            "saved_filename": saved_name,
            "upload_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "password": password,
            "expiration_date": expiration_date,
            "download_limit": download_limit,
            "download_count": 0,
            "file_size": os.path.getsize(local_path),
        })
        
        # Handle AJAX requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": True,
                "file_id": file_id,
                "redirect_url": url_for("main.verify_password", file_id=file_id)
            })
        
        # For non-AJAX requests, redirect to the verification page
        return redirect(url_for("main.verify_password", file_id=file_id))
    
    # GET request - render the upload form
    return render_template("upload.html")

# Add a new route to check file status (optional)
@main.route("/status/<file_id>")
def file_status(file_id):
    file_doc = files_collection.find_one({"file_id": file_id})
    
    if not file_doc:
        return jsonify({"error": "File not found"}), 404
    
    return jsonify({
        "filename": file_doc["filename"],
        "upload_time": file_doc["upload_time"],
        "download_count": file_doc.get("download_count", 0),
        "download_limit": file_doc.get("download_limit", 0),
        "has_password": bool(file_doc.get("password"))
    })

@main.route("/file/<file_id>")
def file_info(file_id):
    file_doc = files_collection.find_one({"file_id": file_id})
    
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
        file_id=file_doc["file_id"],
        file_name=file_doc["filename"],
        file_size=format_file_size(file_doc["file_size"]),
        expiration_date=file_doc.get("expiration_date", "Never"),
        download_limit=file_doc.get("download_limit", 0) or "Unlimited",
        download_url=url_for("main.download", file_id=file_doc["file_id"])
    )