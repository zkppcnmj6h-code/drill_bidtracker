# fetch_njdot.py
import re, requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils_common import open_sheet, upsert_rows

AGENCY = "NJDOT"
SOURCE_URL = "https://www.state.nj.us/transportation/business/procurement/ConstrServ/"

def fetch():
    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []

    # Look for list items with bid-like language
    for li in soup.select("li"):
        txt = " ".join(li.get_text(" ", strip=True).split())
        if not txt:
            continue
        if not re.search(r"\b(bid|proposal|contract|letting|advertisement|solicitation)\b", txt, re.I):
            continue

        a = li.find("a", href=True)
        url = SOURCE_URL
        if a:
            url = a["href"].strip()
            if url.startswith("/"):
                url = "https://www.state.nj.us" + url

        # stable-ish key
        ingest = f"njdot-{abs(hash((txt, url))) & 0xffffffff:08x}"

        out.append({
            "Source": "Direct",
            "Bid Title": txt[:240],
            "Agency": AGENCY,
            "Bid Number": "",
            "Category": "Transportation",
            "Due Date": "",                      # can be enhanced later with regex/dateutil
            "Est. Value ($)": "",
            "Distance (mi)": "",
            "Fit Score (0–100)": "",
            "Status": "Open",
            "URL": url,
            "Notes": "",
            "Prequal_Required (Y/N)": "",
            "Prequal_Expires_On": "",
            "Planholders": "",
            "Addenda_Count": "",
            "Created At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "Ingest Key": ingest,
        })
    return out

def main():
    sh, ws = open_sheet("Bid Tracker v0.1", "Raw Intake")
    existing = set()
    try:
        for r in ws.get_all_records():
            k = r.get("Ingest Key")
            if k:
                existing.add(k)
    except Exception as e:
        print("[NJDOT] Could not read current rows:", e)

    rows = [r for r in fetch() if r["Ingest Key"] not in existing]
    if rows:
        upsert_rows(ws, rows)
        print(f"[NJDOT] Appended: {len(rows)}")
    else:
        print("[NJDOT] No new rows found.")

if __name__ == "__main__":
    main()
