from flask import Blueprint, request, redirect, url_for, render_template, flash, send_file
from pymongo import MongoClient
import os
import uuid
from datetime import datetime

main = Blueprint("main", __name__)
UPLOAD_FOLDER = "uploads"

client = MongoClient("mongodb://mongo:27017/")
db = client["filesharing"]
files_collection = db["uploads"]

@main.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files["file"]
        password = request.form.get("password")
        file_id = str(uuid.uuid4())
        saved_name = f"{file_id}_{uploaded_file.filename}"

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        local_path = os.path.join(UPLOAD_FOLDER, saved_name)
        uploaded_file.save(local_path)

        files_collection.insert_one({
            "file_id": file_id,
            "filename": uploaded_file.filename,
            "saved_filename": saved_name,
            "upload_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "password": password
        })

        return redirect(url_for("main.verify_password", file_id=file_id))

    return '''
    <h2>Upload File</h2>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" required><br><br>
      <input type="text" name="password" placeholder="Set password" required><br><br>
      <input type="submit" value="Upload">
    </form>
    '''

@main.route("/file/<file_id>", methods=["GET", "POST"])
def verify_password(file_id):
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return "❌ File not found", 404

    if request.method == "POST":
        entered_password = request.form.get("password")
        if entered_password == file_doc.get("password"):
            return render_template("download.html", file=file_doc)
        else:
            flash("Incorrect password!", "error")

    return render_template("verify.html", file_id=file_id)

@main.route("/download/<file_id>")
def direct_download(file_id):
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return "❌ File not found", 404

    local_path = os.path.join(UPLOAD_FOLDER, file_doc["saved_filename"])
    if not os.path.exists(local_path):
        return "❌ File not found in storage", 404

    return send_file(local_path, as_attachment=True, download_name=file_doc["filename"])
