import os
import sys
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils_common import upsert_rows, open_sheet

# You can override at runtime without code changes:
#   In Actions → Run workflow → Variables, set NJTA_URL=https://new-url
CANDIDATE_URLS = [
    os.getenv("NJTA_URL", "").strip() or None,
    # Legacy / known patterns (we’ll probe these safely):
    "https://www.njta.com/doing-business/bids-and-rfps",
    "https://www.njta.com/doing-business/procurement/bids",
    "https://www.njta.com/doing-business/procurement/bidding-opportunities",
    "https://www.njta.com/doing-business/procurement",
]
CANDIDATE_URLS = [u for u in CANDIDATE_URLS if u]  # remove Nones/empties
