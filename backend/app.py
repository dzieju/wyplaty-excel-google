"""
Flask backend for Google Sheets access verification.

Endpoints:
- POST /api/upload-sa: Upload a Google Service Account JSON
- GET /api/files: List accessible Google Drive files
- POST /api/start-verify: Start a background verification job
- GET /api/verify-status/<job_id>: Get verification job status
"""

import json
import os
import uuid
from io import BytesIO
from multiprocessing import Manager, Process

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory storage for uploaded service account
service_account_data = {}

# Shared manager for multiprocessing
manager = Manager()
jobs = manager.dict()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_drive_service():
    """Create a Google Drive service using the uploaded service account."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not service_account_data:
        return None

    credentials = service_account.Credentials.from_service_account_info(
        service_account_data,
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ],
    )
    return build("drive", "v3", credentials=credentials)


def get_sheets_service():
    """Create a Google Sheets service using the uploaded service account."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not service_account_data:
        return None

    credentials = service_account.Credentials.from_service_account_info(
        service_account_data,
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ],
    )
    return build("sheets", "v4", credentials=credentials)


def verification_worker(job_id, sa_data, jobs_dict):
    """Background worker that performs verification tasks."""
    import pandas as pd
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    try:
        jobs_dict[job_id] = {"status": "running", "step": "Initializing credentials..."}

        credentials = service_account.Credentials.from_service_account_info(
            sa_data,
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/spreadsheets.readonly",
            ],
        )

        jobs_dict[job_id] = {"status": "running", "step": "Building Drive service..."}
        drive_service = build("drive", "v3", credentials=credentials)

        jobs_dict[job_id] = {"status": "running", "step": "Listing files..."}
        results = (
            drive_service.files()
            .list(
                pageSize=10,
                fields="files(id, name, mimeType)",
                q="mimeType='application/vnd.google-apps.spreadsheet'",
            )
            .execute()
        )
        files = results.get("files", [])

        if not files:
            jobs_dict[job_id] = {
                "status": "completed",
                "result": {
                    "files_found": 0,
                    "message": "No Google Sheets found accessible by this service account.",
                },
            }
            return

        jobs_dict[job_id] = {
            "status": "running",
            "step": f"Found {len(files)} file(s). Exporting first sheet to XLSX...",
        }

        first_file = files[0]
        file_id = first_file["id"]
        file_name = first_file["name"]

        # Export to XLSX
        request_obj = drive_service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        xlsx_buffer = BytesIO()
        downloader = MediaIoBaseDownload(xlsx_buffer, request_obj)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        jobs_dict[job_id] = {"status": "running", "step": "Parsing with pandas..."}

        xlsx_buffer.seek(0)
        df = pd.read_excel(xlsx_buffer, engine="openpyxl")

        sample_data = df.head(5).to_dict(orient="records")
        columns = list(df.columns)
        row_count = len(df)

        jobs_dict[job_id] = {
            "status": "completed",
            "result": {
                "files_found": len(files),
                "exported_file": file_name,
                "columns": columns,
                "row_count": row_count,
                "sample_data": sample_data,
                "message": "Verification successful!",
            },
        }

    except Exception as e:
        jobs_dict[job_id] = {"status": "error", "error": str(e)}


@app.route("/api/upload-sa", methods=["POST"])
def upload_service_account():
    """Upload a Google Service Account JSON file."""
    global service_account_data

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        content = file.read()
        sa_data = json.loads(content)

        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
        ]
        for field in required_fields:
            if field not in sa_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        if sa_data.get("type") != "service_account":
            return jsonify({"error": "Invalid service account type"}), 400

        service_account_data = sa_data

        return jsonify(
            {
                "success": True,
                "message": "Service account uploaded successfully",
                "client_email": sa_data.get("client_email"),
                "project_id": sa_data.get("project_id"),
            }
        )

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files", methods=["GET"])
def list_files():
    """List accessible Google Drive files."""
    if not service_account_data:
        return jsonify({"error": "No service account uploaded"}), 400

    try:
        drive_service = get_drive_service()
        results = (
            drive_service.files()
            .list(
                pageSize=50,
                fields="files(id, name, mimeType, modifiedTime)",
                q="mimeType='application/vnd.google-apps.spreadsheet'",
            )
            .execute()
        )
        files = results.get("files", [])

        return jsonify({"files": files, "count": len(files)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/start-verify", methods=["POST"])
def start_verify():
    """Start a background verification job."""
    if not service_account_data:
        return jsonify({"error": "No service account uploaded"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "step": "Starting..."}

    process = Process(
        target=verification_worker, args=(job_id, service_account_data.copy(), jobs)
    )
    process.start()

    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/verify-status/<job_id>", methods=["GET"])
def verify_status(job_id):
    """Get the status of a verification job."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job_data = dict(jobs[job_id])
    return jsonify({"job_id": job_id, **job_data})


@app.route("/")
def index():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Google Sheets Verification API"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
