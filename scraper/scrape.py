"""
FreeJobAlert Scraper - Maharashtra + Central Govt Jobs ONLY
-------------------------------------------------------------
Sirf ye 9 fields nikalta hai:
  Job Title, Department, Qualification, Category, Last Date,
  Post, Location, Official Website, Apply Link, PDF Link

Jaanbujh kar IGNORE kiya gaya hai:
  - Syllabus, Result, Admit Card, Answer Key, Cutoff pages
  - Kisi bhi doosre state ke jobs (sirf MH + Central rakha hai)

Chalane ka tareeka:
  pip install -r requirements.txt
  python scrape.py

Output: ../site/jobs.json  (website isi file ko padhta hai)
"""

import json
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.freejobalert.com"

# Sirf ye 2 listing sources -> Maharashtra state jobs + All India (Central) jobs
LISTING_PAGES = {
    "Maharashtra": f"{BASE}/maharashtra-government-jobs/",
    "Central": f"{BASE}/government-jobs/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "site" / "jobs.json"

# Category keywords -> agar title/dept me match ho jaaye to category set kar dete hain
CATEGORY_KEYWORDS = {
    "Banking": ["bank", "sbi", "ibps", "rbi", "nabard", "sidbi"],
    "Railway": ["railway", "rrb", "rrc", "metro", "irctc", "konkan railway", "krcl"],
    "Police/Defence": ["police", "army", "navy", "air force", "drdo", "defence",
                        "ordnance", "bsf", "csf", "itbp", "crpf"],
    "Teaching": ["teacher", "professor", "lecturer", "shikshan", "faculty", "tet"],
    "Engineering": ["engineer", "technician", "technical"],
    "Medical/Health": ["nurse", "medical", "mbbs", "aiims", "hospital", "health"],
    "Court/Legal": ["court", "advocate", "legal", "llb"],
}


def guess_category(title, dept):
    text = f"{title} {dept}".lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cat
    return "General"


def job_id(url):
    """URL se ek stable unique id banate hain, taaki duplicate na ho."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return None


def get_listing_links(listing_url):
    """State/Central listing page se saare job article links nikalna."""
    html = fetch(listing_url)
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.select("a[href*='/articles/']"):
        href = a.get("href", "")
        # Sirf recruitment/vacancy waale articles, result/admit-card/syllabus wagera skip
        if any(skip in href.lower() for skip in
               ["result", "admit-card", "answer-key", "syllabus", "cutoff",
                "hall-ticket", "exam-date", "eligibility-", "written-marks"]):
            continue
        if href.startswith("http"):
            links.add(href)
        elif href.startswith("/"):
            links.add(BASE + href)
    return links


def parse_job_page(url, source_state):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Overview table (Recruiting Body, Qualification, Official Website, Location, etc.)
    overview = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).lower()
                val_cell = cells[1]
                val_text = val_cell.get_text(" ", strip=True)
                val_link = val_cell.find("a")
                raw_href = val_link.get("href") if val_link else None
                overview[key] = {
                    "text": val_text,
                    "link": urljoin(url, raw_href) if raw_href else None,
                }

    def get_field(*keys):
        for k in keys:
            for ok, ov in overview.items():
                if k in ok:
                    return ov
        return {"text": "", "link": None}

    dept = get_field("recruiting body", "organisation", "organization", "department").get("text", "")
    quali = get_field("qualification", "eligibility").get("text", "")
    last_date_field = get_field("closing date", "last date")
    last_date = last_date_field.get("text", "")
    post = get_field("post name", "post").get("text", "")
    location = get_field("job location", "location").get("text", "") or source_state
    official_site = get_field("official website")
    official_website = official_site.get("link") or official_site.get("text", "")

    # Important Links section -> Apply Online + Notification PDF
    apply_link = ""
    pdf_link = ""
    APPLY_KEYWORDS = [
        "apply online", "apply here", "apply link", "apply now",
        "online registration", "registration link", "click here to apply",
        "online application",
    ]
    PDF_KEYWORDS = [
        "notification pdf", "official notification", "download notification",
        "notification link", "advertisement pdf", "detailed notification",
    ]
    for li_or_p in soup.find_all(["li", "p"]):
        text = li_or_p.get_text(" ", strip=True).lower()
        a = li_or_p.find("a")
        if not a or not a.get("href"):
            continue
        # har href ko yahin absolute bana do (relative path wala bug fix)
        href = urljoin(url, a.get("href"))
        if not apply_link and any(k in text for k in APPLY_KEYWORDS):
            apply_link = href
        elif not pdf_link and (any(k in text for k in PDF_KEYWORDS) or href.lower().endswith(".pdf")):
            pdf_link = href
        elif "official website" in text and not official_website:
            official_website = href

    # Fallback: kisi bhi .pdf link ko PDF maan lo agar upar nahi mila
    if not pdf_link:
        pdf_a = soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if pdf_a and pdf_a.get("href"):
            pdf_link = urljoin(url, pdf_a.get("href"))

    # Fallback: apply_link kabhi na mile to official_website hi de do,
    # taaki "Apply" button kabhi bhi khaali/broken na jaaye
    if not apply_link:
        apply_link = official_website

    if not last_date:
        # Important Dates table alag format me ho sakta hai
        ld = get_field("last date", "closing date for online registration",
                        "closing date for registration")
        last_date = ld.get("text", "")

    category = guess_category(title, dept)

    return {
        "id": job_id(url),
        "job_title": title,
        "department": dept,
        "qualification": quali,
        "category": category,
        "last_date": last_date,
        "post": post,
        "location": location,
        "official_website": official_website,
        "apply_link": apply_link,
        "pdf_link": pdf_link,
        "source_url": url,
        "state_tag": source_state,   # "Maharashtra" ya "Central"
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def load_existing():
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {job["id"]: job for job in data.get("jobs", [])}
    return {}


def main():
    existing = load_existing()
    all_jobs = dict(existing)  # purane jobs bhi rakhenge (last date aage tak dikhte rahenge)

    for state_name, listing_url in LISTING_PAGES.items():
        print(f"[{state_name}] listing page fetch ho rahi hai...")
        try:
            links = get_listing_links(listing_url)
        except Exception as e:
            print(f"  ERROR fetching listing: {e}")
            continue
        print(f"  {len(links)} job links mile")

        for link in links:
            jid = job_id(link)
            if jid in existing:
                continue  # already scraped pehle, skip (fast + polite)
            try:
                job = parse_job_page(link, state_name)
                if job["job_title"]:
                    all_jobs[jid] = job
                    print(f"  + {job['job_title'][:60]}")
                time.sleep(1)  # rate limit - server par zyada load na daale
            except Exception as e:
                print(f"  ERROR parsing {link}: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "last_synced": datetime.now(timezone.utc).isoformat(),
        "total_jobs": len(all_jobs),
        "jobs": sorted(all_jobs.values(), key=lambda j: j.get("scraped_at", ""), reverse=True),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Total jobs saved: {len(all_jobs)} -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
