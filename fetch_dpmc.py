from utils_common import *
import requests
from bs4 import BeautifulSoup
from datetime import datetime

AGENCY = "NJ DPMC"
SOURCE_URL = "https://www.state.nj.us/treasury/dpmc/contract_search.shtml"

def fetch():
    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []

    # Heuristic: parse rows from tables
    for tr in soup.select("table tr"):
        tds = [normalize(td.get_text(" ")) for td in tr.select("td")]
        if len(tds) < 2: 
            continue

        title = tds[0]
        due   = to_date(" ".join(tds))
        addr  = tds[1] if len(tds) > 1 else "Trenton, NJ"

        link = tr.select_one("a[href]")
        url = (link["href"].strip() if link and link.has_attr("href") else SOURCE_URL)
        if url.startswith("/"):
            url = "https://www.state.nj.us" + url

        row = {
            "Source": "Direct",
            "Bid Title": title[:240],
            "Agency": AGENCY,
            "Bid Number": "",
            "Category": "Building",
            "Due Date": due,
            "Est. Value ($)": "",
            "Distance (mi)": compute_distance(addr),
            "Status": "Open",
            "URL": url,
            "Notes": "",
            "Prequal_Required (Y/N)": "Y",
            "Prequal_Expires_On": "",
            "Planholders": "",
            "Addenda_Count": "",
            "Created At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "Ingest Key": key(AGENCY, "", title),
        }
        row["Fit Score (0–100)"] = compute_fit(row)
        out.append(row)
    return out

def main():
    ws = get_sheet()
    existing = set(ws.col_values(COLUMNS.index("Ingest Key")+1)[1:])
    new = [r for r in fetch() if r["Ingest Key"] not in existing]
    if new:
        append_rows(ws, new)
        print(f"DPMC appended: {len(new)}")
    else:
        print("No new DPMC rows.")

if __name__ == "__main__":
    main()
