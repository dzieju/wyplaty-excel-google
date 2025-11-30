#!/usr/bin/env python3
"""
Prosty Streamlit app do przeglądania Excel i Google Sheets.
Uruchom:
  pip install -r requirements-streamlit.txt
  streamlit run streamlit_app.py

Google Sheets:
- Włącz Google Sheets API i utwórz service account.
- Pobierz JSON z kluczami i udostępnij arkusz adresowi email service account.
- W aplikacji wskaż ścieżkę do pliku JSON lub wklej jego zawartość.
"""
import io
import json

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

st.set_page_config(page_title="Excel / Google Sheets Viewer", layout="wide")

st.title("Excel / Google Sheets Viewer (Python only)")

st.sidebar.header("Źródło danych")
source = st.sidebar.selectbox("Wybierz źródło", ["Upload Excel (.xlsx/.xls/.csv)", "Google Sheets (URL/ID)"])

df = None

if source.startswith("Upload"):
    uploaded = st.sidebar.file_uploader("Wgraj plik Excel (.xlsx/.xls) lub CSV", type=["xlsx", "xls", "csv"])
    sheet_name = st.sidebar.text_input("Nazwa arkusza (opcjonalnie, np. Sheet1)", value="")
    if uploaded is not None:
        try:
            bytes_data = uploaded.read()
            if uploaded.type == "text/csv" or uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(bytes_data))
            else:
                # read_excel can read first sheet or specified sheet_name
                if sheet_name:
                    df = pd.read_excel(io.BytesIO(bytes_data), sheet_name=sheet_name)
                else:
                    # read first sheet
                    df = pd.read_excel(io.BytesIO(bytes_data), sheet_name=0)
            st.success(f"Załadowano: {uploaded.name} — {len(df)} wierszy, {len(df.columns)} kolumn")
        except Exception as e:
            st.error(f"Błąd podczas wczytywania pliku: {e}")

else:  # Google Sheets
    st.sidebar.markdown("Podaj Google Sheets URL lub ID oraz plik JSON service account (albo wklej JSON).")
    sheet_input = st.sidebar.text_input("URL lub ID arkusza")
    sa_option = st.sidebar.selectbox("Sposób autoryzacji", ["Wskaż plik JSON", "Wklej JSON"])
    sa_path = None
    sa_json_text = None
    if sa_option == "Wskaż plik JSON":
        sa_file = st.sidebar.file_uploader("Wgraj service account JSON", type=["json"])
        if sa_file is not None:
            try:
                sa_json_text = sa_file.read().decode("utf-8")
            except Exception:
                sa_json_text = None
    else:
        sa_json_text = st.sidebar.text_area("Wklej tu zawartość service account JSON")

    if st.sidebar.button("Załaduj Google Sheet"):
        if gspread is None:
            st.error("Brakuje wymaganych bibliotek: pip install gspread google-auth")
        elif not sheet_input:
            st.error("Podaj URL lub ID arkusza")
        elif not sa_json_text:
            st.error("Wskaż plik JSON service account lub wklej jego zawartość")
        else:
            try:
                sa_info = json.loads(sa_json_text)
                scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
                creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
                gc = gspread.Client(auth=creds)
                gc.session = gc.auth.authorize(creds)
                # try open by URL or by ID
                try:
                    sh = gc.open_by_url(sheet_input)
                except Exception:
                    # maybe input is ID
                    sh = gc.open_by_key(sheet_input)
                ws = sh.get_worksheet(0)
                records = ws.get_all_records()
                df = pd.DataFrame(records)
                st.success(f"Załadowano Google Sheet: {sh.title} — {len(df)} wierszy, {len(df.columns)} kolumn")
            except Exception as e:
                st.exception(e)

# Wyświetlanie i proste filtrowanie
if df is not None:
    st.subheader("Podgląd danych")
    # podgląd - pokazuj całe, ale paginuj w razie potrzeby
    st.dataframe(df)

    st.markdown("### Filtr i wyszukiwanie")
    cols = list(df.columns)
    if cols:
        col_to_filter = st.selectbox("Kolumna do filtrowania (opcjonalnie)", ["(brak)"] + cols)
        if col_to_filter and col_to_filter != "(brak)":
            val = st.text_input(f"Wartość do wyszukania w kolumnie '{col_to_filter}'")
            if val:
                mask = df[col_to_filter].astype(str).str.contains(val, case=False, na=False)
                st.dataframe(df[mask])
    st.markdown("### Pobierz / Export")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Pobierz CSV", csv, file_name="export.csv", mime="text/csv")
else:
    st.info("Brak danych — wgraj plik Excel lub załaduj Google Sheet z sidebaru.")
