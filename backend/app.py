from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import io
import uuid
import json
import time
from multiprocessing import Process, freeze_support
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd

# Konfiguracja katalogów
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "instance")
VER_DIR = os.path.join(UPLOAD_DIR, "verifications")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VER_DIR, exist_ok=True)
SA_FILENAME = "service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app)


def sa_path():
    return os.path.join(UPLOAD_DIR, SA_FILENAME)


def load_sa_credentials():
    path = sa_path()
    if not os.path.exists(path):
        return None
    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return creds


def write_status(vid, data):
    path = os.path.join(VER_DIR, vid, "status.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_log(vid, text):
    path = os.path.join(VER_DIR, vid, "log.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {text}\n")


def verify_job(vid):
    """
    Zadanie weryfikacyjne uruchamiane jako osobny proces.
    Sprawdza: listowanie plików, próbny eksport pierwszego Google Sheet, odczyt pierwszych wierszy.
    Wynik zapisywany do instance/verifications/<vid>/status.json
    """
    ddir = os.path.join(VER_DIR, vid)
    os.makedirs(ddir, exist_ok=True)
    write_status(vid, {"status": "running", "message": "Rozpoczęto weryfikację..."})
    append_log(vid, "Weryfikacja: start")

    try:
        creds = load_sa_credentials()
        if creds is None:
            write_status(vid, {"status": "failed", "message": "Brak pliku service account. Prześlij go przed weryfikacją."})
            append_log(vid, "Brak pliku service_account.json")
            return

        drive_service = build("drive", "v3", credentials=creds)
        append_log(vid, "Pobieram listę plików (max 100)...")
        results = drive_service.files().list(pageSize=100, fields="files(id, name, mimeType)").execute()
        files = results.get("files", [])
        append_log(vid, f"Znaleziono {len(files)} plików")

        # Zapis listy plików (podstawowe info)
        summary = [{"id": f.get("id"), "name": f.get("name"), "mimeType": f.get("mimeType")} for f in files]
        with open(os.path.join(ddir, "files.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Jeśli są arkusze lub xlsx, spróbuj pobrać pierwszy z nich i odczytać pierwsze wiersze
        target = None
        for f in files:
            if f.get("mimeType") in (
                "application/vnd.google-apps.spreadsheet",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ):
                target = f
                break

        if not target:
            append_log(vid, "Nie znaleziono plików typu Google Sheets ani .xlsx do testowego pobrania.")
            write_status(vid, {"status": "success", "message": "Lista plików pobrana, nie znaleziono arkuszy do testowego pobrania.", "files_count": len(files)})
            return

        append_log(vid, f"Próbne pobranie pliku: {target.get('name')} ({target.get('id')}) type={target.get('mimeType')}")
        if target.get("mimeType") == "application/vnd.google-apps.spreadsheet":
            request_drive = drive_service.files().export_media(fileId=target["id"],
                                                              mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            request_drive = drive_service.files().get_media(fileId=target["id"])

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_drive)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)

        # Parsowanie przez pandas
        append_log(vid, "Parsuję pobrany plik xlsx (pandas)...")
        try:
            xls = pd.read_excel(fh, sheet_name=None)
            sample = {}
            for sheet_name, df in xls.items():
                sample[sheet_name] = df.head(5).to_dict(orient="records")
            # zapisz próbkę
            with open(os.path.join(ddir, "sample.json"), "w", encoding="utf-8") as f:
                json.dump(sample, f, ensure_ascii=False, indent=2)
            append_log(vid, "Parsowanie powiodło się.")
            write_status(vid, {"status": "success", "message": "Weryfikacja zakończona pomyślnie.", "files_count": len(files)})
        except Exception as e:
            append_log(vid, f"Błąd parsowania xlsx: {e}")
            write_status(vid, {"status": "partial", "message": f"Pobrano plik ale wystąpił błąd parsowania: {e}", "files_count": len(files)})
    except Exception as e:
        append_log(vid, f"Exception: {e}")
        write_status(vid, {"status": "failed", "message": str(e)})
    finally:
        append_log(vid, "Weryfikacja: koniec")


@app.route("/api/upload-sa", methods=["POST"])
def upload_sa():
    if 'file' not in request.files:
        return jsonify({"error": "Brak pliku"}), 400
    f = request.files['file']
    if not f.filename.endswith(".json"):
        return jsonify({"error": "Oczekiwany plik .json"}), 400
    save_path = sa_path()
    f.save(save_path)
    return jsonify({"status": "ok", "saved": save_path})


@app.route("/api/files", methods=["GET"])
def list_files():
    creds = load_sa_credentials()
    if creds is None:
        return jsonify({"error": "Brak skonfigurowanego service account. Prześlij plik JSON przez /api/upload-sa"}), 400
    drive_service = build("drive", "v3", credentials=creds)
    results = drive_service.files().list(pageSize=100, fields="files(id, name, mimeType)").execute()
    files = results.get("files", [])
    return jsonify({"files": files})


@app.route("/api/start-verify", methods=["POST"])
def start_verify():
    vid = str(uuid.uuid4())
    ddir = os.path.join(VER_DIR, vid)
    os.makedirs(ddir, exist_ok=True)
    write_status(vid, {"status": "pending", "message": "Oczekuje na uruchomienie..."})
    # Uruchom proces w tle - tylko tutaj tworzony Process, nie podczas importu
    p = Process(target=verify_job, args=(vid,))
    p.daemon = True
    p.start()
    return jsonify({"verification_id": vid})


@app.route("/api/verify-status/<vid>", methods=["GET"])
def verify_status(vid):
    path = os.path.join(VER_DIR, vid, "status.json")
    if not os.path.exists(path):
        return jsonify({"error": "Nie znaleziono takiej weryfikacji"}), 404
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/verify-log/<vid>", methods=["GET"])
def verify_log(vid):
    path = os.path.join(VER_DIR, vid, "log.txt")
    if not os.path.exists(path):
        return jsonify({"error": "Brak logu"}), 404
    return send_file(path, mimetype="text/plain")


@app.route("/api/verify-files/<vid>", methods=["GET"])
def verify_files(vid):
    path = os.path.join(VER_DIR, vid, "files.json")
    if not os.path.exists(path):
        return jsonify({"error": "Brak listy plików"}), 404
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify({"files": data})


@app.route("/api/verify-sample/<vid>", methods=["GET"])
def verify_sample(vid):
    path = os.path.join(VER_DIR, vid, "sample.json")
    if not os.path.exists(path):
        return jsonify({"error": "Brak próbki danych"}), 404
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify({"sample": data})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    index = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index):
        return send_from_directory(app.static_folder, "index.html")
    return jsonify({"message": "Frontend nie jest zbudowany. Uruchom frontend osobno w trybie deweloperskim."})


def main():
    # Dla Windows przy uruchomieniu multiprocessing
    freeze_support()
    # Opcjonalnie: ustawienie metody startu (domyślnie 'spawn' na Windows)
    try:
        import multiprocessing as mp
        mp.set_start_method('spawn', force=False)
    except Exception:
        pass
    # Uruchom Flask
    app.run(port=5000, debug=True)


if __name__ == "__main__":
    main()
