import os, re, hashlib, requests, pandas as pd
from datetime import datetime, date
from dateutil import parser as dateparse
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# -------------------------------
# CONFIG — minimal edits
# -------------------------------
HQ_ZIP = "07039"   # ⟵ EDIT if needed (Drill Co HQ ZIP)
HQ_COORDS = (40.7870, -74.3210)  # Livingston, NJ fallback
GOOGLE_SA_FILE = os.getenv("GOOGLE_SA_FILE", "service_account.json")
SHEET_NAME = os.getenv("SHEET_NAME", "Bid Tracker v0.1")
WORKSHEET = os.getenv("WORKSHEET", "Raw Intake")

COLUMNS = [
    "Source","Bid Title","Agency","Bid Number","Category","Due Date",
    "Est. Value ($)","Distance (mi)","Fit Score (0–100)","Status",
    "URL","Notes","Prequal_Required (Y/N)","Prequal_Expires_On",
    "Planholders","Addenda_Count","Created At","Ingest Key"
]

def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(GOOGLE_SA_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME)
    try:
        ws = sh.worksheet(WORKSHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(WORKSHEET, rows=2000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
    # Align header exactly
    if ws.row_values(1) != COLUMNS:
        try:
            ws.delete_rows(1)
        except Exception:
            pass
        ws.insert_row(COLUMNS, 1)
    return ws

def normalize(s): 
    return re.sub(r"\s+"," ",s or "").strip()

def to_date(s):
    if not s: return ""
    try:
        return dateparse.parse(s, fuzzy=True).strftime("%Y-%m-%d")
    except Exception:
        return ""

def key(agency,bid,title):
    base=f"{normalize(agency)}|{normalize(bid)}|{normalize(title)}".lower()
    return hashlib.sha256(base.encode()).hexdigest()[:16]

def compute_distance(address_or_city):
    """Approx miles HQ → project location. Returns '' on failure."""
    if not address_or_city: return ""
    try:
        geoloc = Nominatim(user_agent="drillco").geocode(address_or_city, timeout=5)
        if not geoloc: return ""
        return round(geodesic(HQ_COORDS, (geoloc.latitude, geoloc.longitude)).miles, 1)
    except Exception:
        return ""

def compute_fit(row: dict) -> int:
    s = 0
    cat = (row.get("Category") or "").lower()
    ag  = (row.get("Agency") or "").upper()
    due = row.get("Due Date") or ""
    dist = row.get("Distance (mi)") or ""
    preq = (row.get("Prequal_Required (Y/N)") or "N").upper()
    exp  = row.get("Prequal_Expires_On") or ""
    val  = row.get("Est. Value ($)") or ""

    # Category focus
    if "transport" in cat: s += 25
    if "building"   in cat: s += 15

    # Agency weight
    if any(k in ag for k in ["NJDOT","TURNPIKE","PANYNJ"]): s += 20
    if "DPMC" in ag: s += 10

    # Contract value bands
    try:
        v = float(str(val).replace(",","").replace("$",""))
        if v > 5_000_000: s += 15
        elif v > 1_000_000: s += 10
        elif v > 250_000: s += 5
    except: 
        pass

    # Distance
    try:
        d = float(dist)
        if d <= 25: s += 15
        elif d <= 50: s += 10
        elif d <= 100: s += 5
        else: s -= 10
    except:
        pass

    # Due date urgency (penalize tight windows)
    try:
        dd = datetime.strptime(due, "%Y-%m-%d").date()
        if (dd - date.today()).days <= 7:
            s -= 10
    except:
        pass

    # Prequalification
    if preq == "Y":
        try:
            e = datetime.strptime(exp, "%Y-%m-%d").date()
            s += 10 if e >= date.today() else -15
        except:
            s -= 5
    else:
        s += 5

    return max(0, min(100, int(s)))

def append_rows(ws, rows):
    df = pd.DataFrame(rows)
    # Ensure all columns exist / order exact
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS]
    ws.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
