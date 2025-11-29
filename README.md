# Wyplaty Excel Google - Config UI Prototype

A configuration UI prototype for verifying Google Sheets access using a Google Service Account.

## Overview

This application allows users to:
1. Upload a Google Service Account JSON file
2. Verify access to Google Sheets by listing accessible files
3. Attempt to export the first Google Sheet to XLSX format
4. Parse a sample of the exported data using pandas

## Project Structure

```
├── backend/           # Flask backend application
│   ├── app.py        # Main Flask application
│   └── requirements.txt
├── frontend/          # Frontend UI
│   └── index.html    # Simple HTML/JS interface
├── README.md
└── .gitignore
```

## Backend API Endpoints

- `POST /api/upload-sa` - Upload a Google Service Account JSON file
- `GET /api/files` - List accessible Google Drive files
- `POST /api/start-verify` - Start a background verification job
- `GET /api/verify-status/<job_id>` - Get the status of a verification job

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The backend will run on http://localhost:5000

### Frontend

Open `frontend/index.html` in a browser or serve it with a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```

Then open http://localhost:8080 in your browser.

## Google Service Account Setup

1. Go to the Google Cloud Console
2. Create a new project or select an existing one
3. Enable the Google Drive API and Google Sheets API
4. Create a Service Account
5. Download the JSON key file
6. Share your Google Sheets with the service account email address

## License

MIT
