import hashlib
import os
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from pymongo import MongoClient

# Load environment variables
load_dotenv()

main = Blueprint("main", __name__)
UPLOAD_FOLDER = "uploads"

# Configure upload folder
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client["filesharing"]
files_collection = db["uploads"]
download_logs = db["download_logs"]

# File type icons mapping
file_type_icons = {
    "image": "fa-file-image",
    "pdf": "fa-file-pdf",
    "word": "fa-file-word",
    "excel": "fa-file-excel",
    "powerpoint": "fa-file-powerpoint",
    "video": "fa-file-video",
    "audio": "fa-file-audio",
    "archive": "fa-file-archive",
    "text": "fa-file-alt",
    "code": "fa-file-code",
    "default": "fa-file",
}


def get_file_icon(filename, content_type):
    """Determine the appropriate Font Awesome icon based on file type"""
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
    elif lowercase_name.endswith((".ppt", ".pptx")):
        return file_type_icons["powerpoint"]
    elif lowercase_name.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return file_type_icons["archive"]
    elif lowercase_name.endswith((".txt", ".rtf", ".md")):
        return file_type_icons["text"]
    elif lowercase_name.endswith(
        (".js", ".py", ".html", ".css", ".php", ".java", ".c", ".cpp")
    ):
        return file_type_icons["code"]

    return file_type_icons["default"]


def encrypt_file(file_path, encryption_level="standard"):
    """Simulated file encryption function

    In a real implementation, this would use different encryption methods
    based on the encryption_level parameter.
    """
    # For this example, we're just returning the original file,
    # but in a real scenario, we'd encrypt with appropriate strength
    return file_path


def send_notification_email(email, message):
    """Send notification email"""
    if not email or not os.getenv("SMTP_SERVER"):
        return False

    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        msg = MIMEMultipart()
        msg["From"] = os.getenv("EMAIL_FROM", "noreply@fileapp.com")
        msg["To"] = email
        msg["Subject"] = "File Sharing Notification"

        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        # Log the error but don't crash the application
        print(f"Email notification error: {str(e)}")
        return False


@main.route("/", methods=["GET"])
def index():
    """Render the file upload form"""
    return """
    <!DOCTYPE html>
<html>
<head>
  <title>Upload File</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f0f2f5;
      margin: 0;
      padding: 20px;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      background: white;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      padding: 30px;
    }
    h1 {
      text-align: center;
      color: #333;
      margin-bottom: 30px;
    }
    .upload-container {
      display: flex;
      flex-wrap: wrap;
      gap: 30px;
    }
    .upload-area {
      flex: 1;
      min-width: 300px;
    }
    .metadata-area {
      flex: 1;
      min-width: 300px;
    }
    .drop-zone {
      border: 2px dashed #ccc;
      border-radius: 8px;
      padding: 30px;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s;
      height: 200px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .drop-zone:hover, .drop-zone.active {
      border-color: #3498db;
      background-color: #f0f7ff;
    }
    .drop-zone i {
      font-size: 48px;
      color: #ccc;
      margin-bottom: 15px;
    }
    .drop-zone.active i, .drop-zone:hover i {
      color: #3498db;
    }
    .drop-zone-text {
      font-size: 16px;
      color: #666;
    }
    .drop-zone button {
      background-color: #3498db;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      margin-top: 15px;
      cursor: pointer;
      font-size: 14px;
    }
    .file-info {
      margin-top: 20px;
      padding: 15px;
      border: 1px solid #e0e0e0;
      border-radius: 5px;
      background: #f9f9f9;
      display: none;
    }
    .file-info p {
      margin: 5px 0;
    }
    .file-info .remove-file {
      color: #e74c3c;
      text-decoration: underline;
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      font-size: 14px;
      margin-top: 10px;
    }
    .form-group {
      margin-bottom: 20px;
    }
    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: bold;
      color: #555;
    }
    .form-group input {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 5px;
      font-size: 16px;
    }
    .form-group textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 5px;
      font-size: 16px;
      min-height: 80px;
      resize: vertical;
    }
    .form-group input[type="date"] {
      font-family: Arial, sans-serif;
    }
    .form-group small {
      display: block;
      margin-top: 5px;
      color: #777;
      font-size: 12px;
    }
    .form-check {
      display: flex;
      align-items: center;
      margin-bottom: 15px;
    }
    .form-check input {
      width: auto;
      margin-right: 10px;
    }
    .submit-btn {
      background-color: #2ecc71;
      color: white;
      border: none;
      padding: 12px;
      width: 100%;
      border-radius: 5px;
      cursor: pointer;
      font-size: 16px;
      margin-top: 10px;
      transition: background-color 0.3s;
    }
    .submit-btn:hover {
      background-color: #27ae60;
    }
    .submit-btn:disabled {
      background-color: #95a5a6;
      cursor: not-allowed;
    }
    .progress-container {
      margin-top: 20px;
      display: none;
    }
    .progress-bar {
      height: 12px;
      background-color: #ecf0f1;
      border-radius: 6px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background-color: #2ecc71;
      width: 0%;
      transition: width 0.3s;
    }
    .progress-text {
      text-align: right;
      font-size: 12px;
      color: #7f8c8d;
      margin-top: 5px;
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid #ddd;
      margin-bottom: 20px;
    }
    .tab {
      padding: 10px 20px;
      cursor: pointer;
      margin-right: 5px;
      border-radius: 5px 5px 0 0;
    }
    .tab.active {
      background-color: #3498db;
      color: white;
    }
    .tab-content {
      display: none;
    }
    .tab-content.active {
      display: block;
    }
    .thumbnail-preview {
      max-width: 100%;
      max-height: 150px;
      margin-top: 10px;
      border-radius: 4px;
      display: none;
    }
    .toggle-container {
      position: relative;
      display: inline-block;
      width: 50px;
      height: 24px;
      margin-right: 10px;
    }
    .toggle-input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: .4s;
      border-radius: 24px;
    }
    .toggle-slider:before {
      position: absolute;
      content: "";
      height: 16px;
      width: 16px;
      left: 4px;
      bottom: 4px;
      background-color: white;
      transition: .4s;
      border-radius: 50%;
    }
    .toggle-input:checked + .toggle-slider {
      background-color: #2196F3;
    }
    .toggle-input:checked + .toggle-slider:before {
      transform: translateX(26px);
    }
    .toggle-label {
      display: flex;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }
    .file-type-icon {
      font-size: 36px;
      margin-right: 10px;
    }
    .encryption-strength {
      margin-top: 20px;
    }
    .encryption-strength label {
      display: block;
      margin-bottom: 8px;
    }
    .strength-options {
      display: flex;
      gap: 10px;
    }
    .strength-option {
      flex: 1;
      text-align: center;
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
    }
    .strength-option.active {
      background-color: #e8f4ff;
      border-color: #3498db;
      color: #3498db;
    }
    .notification-options {
      margin-top: 10px;
    }
    .notification-label {
      display: block;
      margin-bottom: 8px;
      font-weight: bold;
    }
    #email-notifications {
      display: none;
      margin-top: 10px;
    }
    @media screen and (max-width: 768px) {
      .upload-container {
        flex-direction: column;
      }
      .tabs {
        flex-direction: column;
      }
      .tab {
        border-radius: 0;
        margin-right: 0;
        margin-bottom: 1px;
      }
    }
  </style>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
  <div class="container">
    <h1>Secure File Sharing</h1>
    
    <div class="tabs">
      <div class="tab active" data-tab="upload">Upload File</div>
      <div class="tab" data-tab="options">Advanced Options</div>
    </div>
    
    <form id="upload-form" action="{{ url_for('main.index') }}" method="POST" enctype="multipart/form-data">
      <div class="tab-content active" id="upload-tab">
        <div class="upload-container">
          <!-- File Upload Area -->
          <div class="upload-area">
            <div id="drop-zone" class="drop-zone">
              <i class="fas fa-cloud-upload-alt"></i>
              <p class="drop-zone-text">Drag and drop files here</p>
              <p class="drop-zone-text">or</p>
              <button type="button" id="browse-btn">Browse Files</button>
              <input type="file" id="file-input" name="file" style="display: none;">
            </div>
            
            <div id="file-info" class="file-info">
              <div style="display: flex; align-items: center;">
                <span id="file-type-icon" class="file-type-icon"><i class="fas fa-file"></i></span>
                <div>
                  <p><strong>File Name:</strong> <span id="file-name"></span></p>
                  <p><strong>File Size:</strong> <span id="file-size"></span></p>
                  <p><strong>File Type:</strong> <span id="file-type"></span></p>
                </div>
              </div>
              <img id="thumbnail-preview" class="thumbnail-preview">
              <button type="button" class="remove-file" id="remove-file">Remove File</button>
            </div>
            
            <div id="progress-container" class="progress-container">
              <div class="progress-bar">
                <div id="progress-fill" class="progress-fill"></div>
              </div>
              <p class="progress-text"><span id="progress-percentage">0%</span> uploaded</p>
            </div>
          </div>
          
          <!-- Metadata Area -->
          <div class="metadata-area">
            <div class="form-group">
              <label for="password">Password</label>
              <input type="password" id="password" name="password" required>
              <small>Recipients will need this password to access the file</small>
            </div>
            
            <div class="form-group">
              <label for="expiration-date">Expiration Date</label>
              <input type="date" id="expiration-date" name="expiration-date">
              <small>File will be deleted after this date (optional)</small>
            </div>
            
            <div class="form-group">
              <label for="download-limit">Download Limit</label>
              <input type="number" id="download-limit" name="download-limit" min="0" placeholder="Unlimited">
              <small>Maximum number of downloads allowed (optional)</small>
            </div>
            
            <div class="form-group">
              <label for="description">File Description</label>
              <textarea id="description" name="description" placeholder="Add a description of this file"></textarea>
              <small>Help recipients understand what this file contains</small>
            </div>
            
            <div class="form-group notification-options">
              <label class="notification-label">Notification Options</label>
              <div class="form-check">
                <label class="toggle-label">
                  <div class="toggle-container">
                    <input type="checkbox" id="notify-download" name="notify-download" class="toggle-input">
                    <span class="toggle-slider"></span>
                  </div>
                  Notify me when file is downloaded
                </label>
              </div>
              
              <div id="email-notifications">
                <input type="email" id="notification-email" name="notification-email" placeholder="Your email address" class="form-control">
              </div>
            </div>
            
            <button type="submit" id="submit-btn" class="submit-btn" disabled>Upload File</button>
          </div>
        </div>
      </div>
      
      <div class="tab-content" id="options-tab">
        <div class="form-group">
          <label for="filename-override">Custom Filename (optional)</label>
          <input type="text" id="filename-override" name="filename-override">
          <small>Rename your file for recipients</small>
        </div>
        
        <div class="form-group encryption-strength">
          <label>Encryption Strength</label>
          <div class="strength-options">
            <div class="strength-option active" data-value="standard">
              <i class="fas fa-lock"></i>
              <p>Standard</p>
            </div>
            <div class="strength-option" data-value="high">
              <i class="fas fa-shield-alt"></i>
              <p>High</p>
            </div>
            <div class="strength-option" data-value="maximum">
              <i class="fas fa-user-shield"></i>
              <p>Maximum</p>
            </div>
          </div>
          <input type="hidden" name="encryption-level" id="encryption-level" value="standard">
        </div>
        
        <div class="form-check">
          <input type="checkbox" id="allow-preview" name="allow-preview" checked>
          <label for="allow-preview">Allow recipients to preview file before download</label>
        </div>
        
        <div class="form-check">
          <input type="checkbox" id="collect-recipient-data" name="collect-recipient-data">
          <label for="collect-recipient-data">Collect recipient email address before download</label>
        </div>
        
        <div class="form-check">
          <input type="checkbox" id="self-destruct" name="self-destruct">
          <label for="self-destruct">One-time download (file deletes after first download)</label>
        </div>
      </div>
    </form>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', function() {
      const dropZone = document.getElementById('drop-zone');
      const fileInput = document.getElementById('file-input');
      const browseBtn = document.getElementById('browse-btn');
      const fileInfo = document.getElementById('file-info');
      const fileName = document.getElementById('file-name');
      const fileSize = document.getElementById('file-size');
      const fileType = document.getElementById('file-type');
      const fileTypeIcon = document.getElementById('file-type-icon');
      const thumbnailPreview = document.getElementById('thumbnail-preview');
      const removeFile = document.getElementById('remove-file');
      const submitBtn = document.getElementById('submit-btn');
      const progressContainer = document.getElementById('progress-container');
      const progressFill = document.getElementById('progress-fill');
      const progressPercentage = document.getElementById('progress-percentage');
      const uploadForm = document.getElementById('upload-form');
      const tabs = document.querySelectorAll('.tab');
      const tabContents = document.querySelectorAll('.tab-content');
      const strengthOptions = document.querySelectorAll('.strength-option');
      const encryptionLevel = document.getElementById('encryption-level');
      const notifyDownload = document.getElementById('notify-download');
      const emailNotifications = document.getElementById('email-notifications');
      
      // Tab switching
      tabs.forEach(tab => {
        tab.addEventListener('click', function() {
          tabs.forEach(t => t.classList.remove('active'));
          tabContents.forEach(c => c.classList.remove('active'));
          this.classList.add('active');
          const tabId = this.getAttribute('data-tab') + '-tab';
          document.getElementById(tabId).classList.add('active');
        });
      });
      
      // Strength options
      strengthOptions.forEach(option => {
        option.addEventListener('click', function() {
          strengthOptions.forEach(o => o.classList.remove('active'));
          this.classList.add('active');
          encryptionLevel.value = this.getAttribute('data-value');
        });
      });
      
      // Toggle notification email
      notifyDownload.addEventListener('change', function() {
        emailNotifications.style.display = this.checked ? 'block' : 'none';
      });
      
      // Open file dialog when browse button is clicked
      browseBtn.addEventListener('click', function() {
        fileInput.click();
      });
      
      // Handle file selection
      fileInput.addEventListener('change', function() {
        if (fileInput.files.length > 0) {
          displayFileInfo(fileInput.files[0]);
        }
      });
      
      // Handle drag events
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
      });
      
      function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
      });
      
      ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
      });
      
      function highlight() {
        dropZone.classList.add('active');
      }
      
      function unhighlight() {
        dropZone.classList.remove('active');
      }
      
      // Handle dropped files
      dropZone.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
          fileInput.files = files;
          displayFileInfo(files[0]);
        }
      });
      
      // Display file information with improved file type detection
      function displayFileInfo(file) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileType.textContent = file.type || 'Unknown';
        
        // Set appropriate icon based on file type
        let iconClass = 'fa-file';
        
        if (file.type.includes('image')) {
          iconClass = 'fa-file-image';
          // Preview image if it's an image file
          const reader = new FileReader();
          reader.onload = function(e) {
            thumbnailPreview.src = e.target.result;
            thumbnailPreview.style.display = 'block';
          };
          reader.readAsDataURL(file);
        } else if (file.type.includes('pdf')) {
          iconClass = 'fa-file-pdf';
        } else if (file.type.includes('word') || file.name.endsWith('.doc') || file.name.endsWith('.docx')) {
          iconClass = 'fa-file-word';
        } else if (file.type.includes('excel') || file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
          iconClass = 'fa-file-excel';
        } else if (file.type.includes('video')) {
          iconClass = 'fa-file-video';
        } else if (file.type.includes('audio')) {
          iconClass = 'fa-file-audio';
        } else if (file.type.includes('zip') || file.type.includes('compressed')) {
          iconClass = 'fa-file-archive';
        } else if (file.type.includes('text')) {
          iconClass = 'fa-file-alt';
        }
        
        fileTypeIcon.innerHTML = `<i class="fas ${iconClass}"></i>`;
        fileInfo.style.display = 'block';
        thumbnailPreview.style.display = file.type.includes('image') ? 'block' : 'none';
        submitBtn.disabled = false;
        
        // Automatically fill custom filename field
        const filenameOverride = document.getElementById('filename-override');
        if (filenameOverride && !filenameOverride.value) {
          filenameOverride.value = file.name;
        }
      }
      
      // Format file size
      function formatFileSize(bytes) {
        if (bytes < 1024) {
          return bytes + ' bytes';
        } else if (bytes < 1048576) {
          return (bytes / 1024).toFixed(1) + ' KB';
        } else {
          return (bytes / 1048576).toFixed(1) + ' MB';
        }
      }
      
      // Remove selected file
      removeFile.addEventListener('click', function() {
        fileInput.value = '';
        fileInfo.style.display = 'none';
        thumbnailPreview.style.display = 'none';
        thumbnailPreview.src = '';
        submitBtn.disabled = true;
      });
      
      // Handle form submission
      uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!fileInput.files.length) {
          alert('Please select a file to upload');
          return;
        }
        
        const formData = new FormData(uploadForm);
        
        // Show progress bar
        progressContainer.style.display = 'block';
        submitBtn.disabled = true;
        
        // Use XMLHttpRequest for upload with progress
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', function(e) {
          if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            progressFill.style.width = percentComplete + '%';
            progressPercentage.textContent = percentComplete + '%';
          }
        });
        
        xhr.addEventListener('load', function() {
          if (xhr.status >= 200 && xhr.status < 300) {
            // Success - redirect to the URL returned from the server
            try {
              const response = JSON.parse(xhr.responseText);
              window.location.href = response.redirect_url || '/';
            } catch (e) {
              // If response is not JSON, just redirect to home
              window.location.href = '/';
            }
          } else {
            // Error
            alert('Upload failed. Please try again.');
            submitBtn.disabled = false;
          }
        });
        
        xhr.addEventListener('error', function() {
          alert('Upload failed. Please try again.');
          submitBtn.disabled = false;
        });
        
        // Set up and send the request
        xhr.open('POST', uploadForm.action, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.send(formData);
      });
    });
  </script>
</body>
</html>
    """


@main.route("/", methods=["POST"])
def upload_file():
    """Handle file upload and metadata"""
    # Check if a file was uploaded
    if "file" not in request.files:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "No file part"}), 400
        flash("No file part", "error")
        return redirect(request.url)

    file = request.files["file"]

    # Check if a file was selected
    if file.filename == "":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "No file selected"}), 400
        flash("No file selected", "error")
        return redirect(request.url)

    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())

    # Get metadata from the form
    password = request.form.get("password", "")
    expiration_date = request.form.get("expiration-date", "")  # Note the hyphen
    download_limit = request.form.get("download-limit", "0")  # Note the hyphen
    description = request.form.get("description", "")

    # Advanced options
    filename_override = request.form.get("filename-override", "")
    encryption_level = request.form.get("encryption-level", "standard")
    allow_preview = "allow-preview" in request.form
    collect_recipient_data = "collect-recipient-data" in request.form
    self_destruct = "self-destruct" in request.form
    notify_download = "notify-download" in request.form
    notification_email = request.form.get("notification-email", "")

    # Convert download_limit to integer
    try:
        download_limit = int(download_limit) if download_limit else 0
    except ValueError:
        download_limit = 0

    # Save the file with a unique name
    original_filename = file.filename
    display_filename = filename_override or original_filename
    saved_name = f"{file_id}_{original_filename}"
    local_path = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(local_path)

    # Encrypt file if encryption is enabled
    if encryption_level != "standard":
        local_path = encrypt_file(local_path, encryption_level)

    # Get file information
    file_size = os.path.getsize(local_path)
    content_type = file.content_type
    file_icon = get_file_icon(original_filename, content_type)

    # Create a hash of the file for integrity verification
    file_hash = ""
    if os.path.exists(local_path):
        with open(local_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

    # Save metadata to MongoDB
    file_data = {
        "file_id": file_id,
        "original_filename": original_filename,
        "display_filename": display_filename,
        "saved_filename": saved_name,
        "file_path": local_path,
        "file_size": file_size,
        "content_type": content_type,
        "file_icon": file_icon,
        "file_hash": file_hash,
        "upload_time": datetime.utcnow(),
        "password": password,
        "expiration_date": expiration_date,
        "download_limit": download_limit,
        "download_count": 0,
        "description": description,
        "allow_preview": allow_preview,
        "collect_recipient_data": collect_recipient_data,
        "self_destruct": self_destruct,
        "encryption_level": encryption_level,
        "notify_download": notify_download,
        "notification_email": notification_email if notify_download else "",
    }

    files_collection.insert_one(file_data)

    # Handle AJAX requests
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "success": True,
                "file_id": file_id,
                "message": "File uploaded successfully",
                "redirect_url": url_for("main.verify_password", file_id=file_id),
            }
        )

    # For regular form submit, redirect to success page
    return redirect(url_for("main.verify_password", file_id=file_id))


@main.route("/file/<file_id>", methods=["GET", "POST"])
def verify_password(file_id):
    """Password verification screen"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    # Check if file is expired
    if file_doc.get("expiration_date"):
        try:
            expiration_date = datetime.strptime(file_doc["expiration_date"], "%Y-%m-%d")
            if datetime.utcnow() > expiration_date:
                flash("This file has expired and is no longer available", "error")
                return redirect(url_for("main.index"))
        except ValueError:
            # If date format is invalid, just ignore expiration check
            pass

    # Check if download limit is reached
    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        flash("Download limit reached for this file", "error")
        return redirect(url_for("main.index"))

    # Handle form submission (password verification)
    if request.method == "POST":
        entered_password = request.form.get("password", "")

        # Verify password
        if file_doc.get("password") and entered_password != file_doc["password"]:
            flash("Incorrect password", "error")
            return render_template("verify.html", file_id=file_id)

        # If collect_recipient_data is enabled, collect email before download
        if file_doc.get("collect_recipient_data"):
            recipient_email = request.form.get("recipient_email", "")
            if not recipient_email:
                # If no email provided, show email collection form
                return render_template("collect_email.html", file_id=file_id)

            # Save the recipient email in the session for logging
            session["recipient_email"] = recipient_email

        # Password is correct, redirect to download or preview page
        if file_doc.get("allow_preview", True):
            return redirect(url_for("main.file_preview", file_id=file_id))
        else:
            # Direct download
            return redirect(url_for("main.direct_download", file_id=file_id))

    # GET request - show password verification form
    collect_email = file_doc.get("collect_recipient_data", False) and not file_doc.get(
        "password"
    )

    if collect_email:
        # If no password but email collection is enabled, show email form
        return render_template("collect_email.html", file_id=file_id)

    # Show password form if password is set
    if file_doc.get("password"):
        return render_template("verify.html", file_id=file_id)

    # No password and no email collection, go directly to download/preview
    if file_doc.get("allow_preview", True):
        return redirect(url_for("main.file_preview", file_id=file_id))
    else:
        return redirect(url_for("main.direct_download", file_id=file_id))


@main.route("/preview/<file_id>")
def file_preview(file_id):
    """Preview file before downloading"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    # Render preview template with file details
    return render_template("preview.html", file=file_doc)


@main.route("/download/<file_id>")
def direct_download(file_id):
    """Process file download"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    local_path = file_doc.get("file_path")
    if not os.path.exists(local_path):
        flash("File not found on server", "error")
        return redirect(url_for("main.index"))

    # Log the download
    download_info = {
        "file_id": file_id,
        "download_time": datetime.utcnow(),
        "ip_address": request.remote_addr,
        "user_agent": request.user_agent.string,
        "recipient_email": session.get("recipient_email", ""),
    }
    download_logs.insert_one(download_info)

    # Increment download counter
    files_collection.update_one({"file_id": file_id}, {"$inc": {"download_count": 1}})

    # Send notification if enabled
    if file_doc.get("notify_download") and file_doc.get("notification_email"):
        file_name = file_doc.get("display_filename") or file_doc.get(
            "original_filename"
        )
        message = f"Your file '{file_name}' was downloaded on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}."

        if download_info.get("recipient_email"):
            message += f"\nRecipient email: {download_info['recipient_email']}"

        send_notification_email(file_doc["notification_email"], message)

    # If this is a self-destruct file, mark for deletion after download
    if file_doc.get("self_destruct"):
        files_collection.update_one(
            {"file_id": file_id}, {"$set": {"marked_for_deletion": True}}
        )

    # Clear session data
    if "recipient_email" in session:
        session.pop("recipient_email")

    # Send the file
    return send_file(
        local_path,
        as_attachment=True,
        download_name=file_doc.get("display_filename")
        or file_doc.get("original_filename"),
    )


@main.route("/api/file-info/<file_id>")
def file_info_api(file_id):
    """API endpoint to get file information"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return jsonify({"error": "File not found"}), 404

    # Return only non-sensitive file details
    file_info = {
        "filename": file_doc.get("display_filename")
        or file_doc.get("original_filename"),
        "file_size": file_doc.get("file_size"),
        "content_type": file_doc.get("content_type"),
        "upload_time": file_doc.get("upload_time"),
        "download_count": file_doc.get("download_count", 0),
        "download_limit": file_doc.get("download_limit", 0),
        "has_password": bool(file_doc.get("password")),
        "description": file_doc.get("description", ""),
        "file_icon": file_doc.get("file_icon", "fa-file"),
        "allow_preview": file_doc.get("allow_preview", True),
    }

    return jsonify(file_info)


# Maintenance route to clean up expired files (would be called by a cron job)
@main.route("/maintenance/cleanup", methods=["POST"])
def cleanup_files():
    """Cleanup expired and self-destructed files"""
    # This route should be protected in production!
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != os.getenv("MAINTENANCE_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    current_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Find expired files
    expired_files = files_collection.find(
        {
            "$or": [
                {"expiration_date": {"$lt": current_date}},
                {"marked_for_deletion": True},
            ]
        }
    )

    deleted_count = 0
    for file in expired_files:
        # Delete the actual file
        try:
            if os.path.exists(file.get("file_path", "")):
                os.remove(file.get("file_path"))
        except Exception as e:
            print(f"Error deleting file {file.get('file_id')}: {str(e)}")

        # Remove from database
        files_collection.delete_one({"_id": file["_id"]})
        deleted_count += 1

    return jsonify(
        {
            "success": True,
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    # Add this route to routes_extended.py


@main.route("/preview/content/<file_id>")
def file_preview_content(file_id):
    """Serve file content for preview purposes"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return "File not found", 404

    local_path = file_doc.get("file_path")
    if not os.path.exists(local_path):
        return "File not found on server", 404

    # For security, we should check if the file type is safe to preview
    # This is a simplified version - in production, you'd want more thorough checks
    content_type = file_doc.get("content_type", "")
    safe_to_preview = (
        content_type.startswith("image/")
        or content_type.startswith("text/")
        or content_type.startswith("audio/")
        or content_type.startswith("video/")
        or content_type == "application/pdf"
    )

    if not safe_to_preview:
        return "File type not supported for preview", 400

    # If file should be safe to preview, serve it inline
    return send_file(local_path, mimetype=content_type, as_attachment=False)


@main.route("/stats/files")
def file_stats():
    """Show admin statistics about files (protected route)"""
    # This should be protected with authentication in production
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != os.getenv("MAINTENANCE_API_KEY"):
        return "Unauthorized", 401

    # Get statistics from MongoDB
    total_files = files_collection.count_documents({})
    total_downloads = download_logs.count_documents({})

    # Get total storage used
    total_size = 0
    for file in files_collection.find({}, {"file_size": 1}):
        total_size += file.get("file_size", 0)

    # Format total size
    if total_size < 1024:
        formatted_size = f"{total_size} bytes"
    elif total_size < 1024 * 1024:
        formatted_size = f"{total_size / 1024:.2f} KB"
    else:
        formatted_size = f"{total_size / (1024 * 1024):.2f} MB"

    # Get file types distribution
    file_types = {}
    for file in files_collection.find({}, {"content_type": 1}):
        content_type = file.get("content_type", "unknown")
        main_type = content_type.split("/")[0] if "/" in content_type else content_type
        file_types[main_type] = file_types.get(main_type, 0) + 1

    return jsonify(
        {
            "total_files": total_files,
            "total_downloads": total_downloads,
            "total_storage": formatted_size,
            "file_types": file_types,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@main.route("/history/<days>")
def download_history(days):
    """Get download history for recent days (protected route)"""
    try:
        days = int(days)
    except ValueError:
        days = 7  # Default to one week

    # This should be protected with authentication in production
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != os.getenv("MAINTENANCE_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query MongoDB for download history
    downloads = download_logs.find(
        {"download_time": {"$gte": start_date, "$lte": end_date}}
    ).sort("download_time", -1)  # Sort by newest first

    # Format results
    history = []
    for download in downloads:
        # Get file info
        file_id = download.get("file_id")
        file_info = files_collection.find_one({"file_id": file_id})

        if file_info:
            file_name = file_info.get("display_filename") or file_info.get(
                "original_filename"
            )
        else:
            file_name = "File no longer exists"

        history.append(
            {
                "file_id": file_id,
                "file_name": file_name,
                "download_time": download.get("download_time").strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "ip_address": download.get("ip_address"),
                "recipient_email": download.get("recipient_email", "Not provided"),
            }
        )

    return jsonify({"history": history, "days": days, "total_records": len(history)})


@main.route("/share/<file_id>")
def share_page(file_id):
    """Public share page for a file"""
    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        flash("File not found", "error")
        return redirect(url_for("main.index"))

    # Check if file is expired
    if file_doc.get("expiration_date"):
        try:
            expiration_date = datetime.strptime(file_doc["expiration_date"], "%Y-%m-%d")
            if datetime.utcnow() > expiration_date:
                return render_template("expired.html")
        except ValueError:
            # If date format is invalid, just ignore expiration check
            pass

    # Check if download limit is reached
    if (
        file_doc.get("download_limit")
        and file_doc["download_count"] >= file_doc["download_limit"]
    ):
        return render_template("limit_reached.html")

    # Render share page with minimal file info
    return render_template(
        "share.html",
        file_id=file_id,
        filename=file_doc.get("display_filename") or file_doc.get("original_filename"),
        file_size=file_doc.get("file_size", 0),
        file_icon=file_doc.get("file_icon", "fa-file"),
        has_password=bool(file_doc.get("password")),
        collect_email=file_doc.get("collect_recipient_data", False),
    )


@main.route("/generate_qr/<file_id>")
def generate_qr(file_id):
    """Generate QR code for file sharing"""
    from io import BytesIO

    import qrcode

    file_doc = files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return "File not found", 404

    # Create the sharing URL
    share_url = url_for("main.share_page", file_id=file_id, _external=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(share_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save to memory buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Return image
    return send_file(buffer, mimetype="image/png")
