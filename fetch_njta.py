from utils_common import *
import requests, re
from bs4 import BeautifulSoup
from datetime import datetime

AGENCY = "NJ Turnpike Authority"
SOURCE_URL = "https://www.njta.com/doing-business/bids-and-rfps"  # adjust if actual page differs

def fetch():
    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()

    candidates = soup.select("table tr, ul li, ol li, div a, section a")
    for node in candidates:
        text = normalize(node.get_text(" "))
        if not re.search(r"\b(Bid|RFP|Proposal|Contract|Solicitation)\b", text, re.I):
            continue

        link = node if node.name == "a" else node.select_one("a[href]")
        url = (link["href"].strip() if link and link.has_attr("href") else SOURCE_URL)
        if url.startswith("/"): url = "https://www.njta.com" + url

        bidno = ""
        m = re.search(r"(Bid|Contract)\s*#\s*([A-Za-z0-9\-]+)", text, re.I)
        if m: bidno = m.group(2)

        row = {
            "Source": "Direct",
            "Bid Title": text[:240],
            "Agency": AGENCY,
            "Bid Number": bidno,
            "Category": "Transportation",
            "Due Date": to_date(text),
            "Est. Value ($)": "",
            "Distance (mi)": compute_distance("Woodbridge, NJ"),
            "Status": "Open",
            "URL": url,
            "Notes": "",
            "Prequal_Required (Y/N)": "Y",
            "Prequal_Expires_On": "",
            "Planholders": "",      # enhancement possible by following detail links
            "Addenda_Count": "",    # enhancement possible
            "Created At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        row["Fit Score (0–100)"] = compute_fit(row)
        row["Ingest Key"] = key(AGENCY, bidno, row["Bid Title"])
        if row["Ingest Key"] in seen:
            continue
        seen.add(row["Ingest Key"])
        out.append(row)
    return out

def main():
    ws = get_sheet()
    existing = set(ws.col_values(COLUMNS.index("Ingest Key")+1)[1:])
    new = [r for r in fetch() if r["Ingest Key"] not in existing]
    if new:
        append_rows(ws, new)
        print(f"NJTA appended: {len(new)}")
    else:
        print("No new NJTA rows.")

if __name__ == "__main__":
    main()
