#!/usr/bin/env python3
"""
Automated ORCID Publication Checker for Allison Welch's Portfolio

This script:
1. Fetches publications from ORCID API (public, no auth needed)
2. Compares against the existing publications.json
3. If new publications are found, updates publications.json AND publications.html
4. The GitHub Action will then create a PR for review

ORCID ID: 0000-0002-2314-7625
"""

import html as html_module
import json
import os
import re
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

ORCID_ID = "0000-0002-2314-7625"
ORCID_API_BASE = f"https://pub.orcid.org/v3.0/{ORCID_ID}"
PUBS_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "data", "publications.json")
PUBS_HTML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "publications.html")


# ---------------------------------------------------------------------------
# ORCID API helpers
# ---------------------------------------------------------------------------

def _get_json(url):
    headers = {"Accept": "application/json", "User-Agent": "AllisonWelchPortfolio/1.0"}
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Warning: request failed for {url}: {e}")
        return None


def fetch_orcid_works():
    """Fetch all work summaries from ORCID."""
    data = _get_json(f"{ORCID_API_BASE}/works")
    if data is None:
        print("Error: could not fetch ORCID works.")
        sys.exit(1)
    return data


def fetch_work_details(put_code):
    """Fetch full work record (includes contributor list) for a single put-code."""
    return _get_json(f"{ORCID_API_BASE}/work/{put_code}")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_contributors(work_detail):
    """Return list of contributor name strings from a full work record."""
    if not work_detail:
        return []
    contributors = (
        work_detail
        .get("contributors", {})
        .get("contributor", [])
    )
    names = []
    for c in contributors:
        credit = c.get("credit-name") or {}
        name = credit.get("value", "").strip()
        if name:
            names.append(name)
    return names


def format_authors(names):
    """
    Build an HTML author string.
    Names matching 'Welch' are wrapped in <strong>.
    Final pair joined with ', &amp; '.
    """
    if not names:
        return ""
    formatted = []
    for name in names:
        escaped = html_module.escape(name)
        if "welch" in name.lower():
            escaped = f"<strong>{escaped}</strong>"
        formatted.append(escaped)
    if len(formatted) == 1:
        return formatted[0]
    return ", ".join(formatted[:-1]) + ", &amp; " + formatted[-1]


def get_section_id(work_type):
    """Map an ORCID work-type string to the HTML section id."""
    t = (work_type or "").upper()
    if "DATA_SET" in t or "DATASET" in t:
        return "datasets"
    return "journal-articles"


def parse_works(orcid_data):
    """Parse ORCID work summaries into a list of dicts (no author info yet)."""
    publications = []
    for group in orcid_data.get("group", []):
        summary = group.get("work-summary", [{}])[0]

        title_obj = summary.get("title") or {}
        title = (title_obj.get("title") or {}).get("value", "Unknown Title")

        pub_date = summary.get("publication-date") or {}
        year  = (pub_date.get("year")  or {}).get("value", "")
        month = (pub_date.get("month") or {}).get("value", "")

        journal_obj = summary.get("journal-title") or {}
        journal = journal_obj.get("value", "")

        doi = ""
        for ext in (summary.get("external-ids") or {}).get("external-id", []):
            if ext.get("external-id-type") == "doi":
                doi = ext.get("external-id-value", "")
                break

        publications.append({
            "title":     title,
            "year":      year,
            "month":     month,
            "journal":   journal,
            "doi":       doi,
            "type":      summary.get("type", ""),
            "put_code":  str(summary.get("put-code", "")),
        })

    publications.sort(key=lambda x: x.get("year", "0"), reverse=True)
    return publications


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

def load_existing_publications():
    if os.path.exists(PUBS_JSON):
        with open(PUBS_JSON) as f:
            return json.load(f)
    return []


def save_publications(publications):
    os.makedirs(os.path.dirname(PUBS_JSON), exist_ok=True)
    with open(PUBS_JSON, "w") as f:
        json.dump(publications, f, indent=2)
    print(f"Saved {len(publications)} publications to {PUBS_JSON}")


def find_new_publications(current, existing):
    existing_dois   = {p.get("doi", "").lower()   for p in existing if p.get("doi")}
    existing_titles = {p.get("title", "").lower()  for p in existing if p.get("title")}
    new_pubs = []
    for pub in current:
        doi   = pub.get("doi",   "").lower()
        title = pub.get("title", "").lower()
        if doi   and doi   in existing_dois:   continue
        if title and title in existing_titles: continue
        new_pubs.append(pub)
    return new_pubs


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_pub_html_entry(pub):
    """
    Generate a <div class="pub-item"> block matching the hand-authored HTML format.
    Indentation: 28 spaces for the outer div (matching the rest of the file).
    """
    I0 = " " * 28   # pub-item
    I1 = " " * 32   # pub-year / pub-details
    I2 = " " * 36   # pub-title / pub-authors / pub-journal / pub-links
    I3 = " " * 40   # <a> inside pub-links

    year    = html_module.escape(pub.get("year",    ""))
    title   = html_module.escape(pub.get("title",   ""))
    authors = pub.get("authors_html", "")   # already HTML-formatted
    journal = html_module.escape(pub.get("journal", ""))
    doi     = pub.get("doi", "")

    authors_line = f"\n{I2}<div class=\"pub-authors\">{authors}</div>" if authors else ""

    doi_link = ""
    if doi:
        doi_link = (
            f"\n{I3}<a href=\"https://doi.org/{doi}\" "
            f"class=\"btn btn--small\" target=\"_blank\" rel=\"noopener\">DOI</a>"
        )

    return (
        f"{I0}<div class=\"pub-item\">\n"
        f"{I1}<div class=\"pub-year\">{year}</div>\n"
        f"{I1}<div class=\"pub-details\">\n"
        f"{I2}<div class=\"pub-title\">{title}</div>"
        f"{authors_line}\n"
        f"{I2}<div class=\"pub-journal\">{journal}</div>\n"
        f"{I2}<div class=\"pub-links\">"
        f"{doi_link}\n"
        f"{I2}</div>\n"
        f"{I1}</div>\n"
        f"{I0}</div>"
    )


# ---------------------------------------------------------------------------
# HTML insertion
# ---------------------------------------------------------------------------

def insert_pub_into_section(html_content, section_id, new_entry_html, pub_year):
    """
    Insert new_entry_html into the pub-list of the named section.
    Entries are ordered year-descending; the new entry is placed before the
    first existing entry whose year is strictly less than pub_year.
    Falls back to inserting at the top of the pub-list if no such entry exists.
    """
    section_marker = f'<section id="{section_id}">'
    section_start = html_content.find(section_marker)
    if section_start == -1:
        print(f"  Warning: section #{section_id} not found in publications.html — skipping")
        return html_content

    pub_list_marker = '<div class="pub-list">'
    pub_list_pos = html_content.find(pub_list_marker, section_start)
    if pub_list_pos == -1:
        print(f"  Warning: pub-list not found in section #{section_id} — skipping")
        return html_content

    after_open_tag = pub_list_pos + len(pub_list_marker)

    # Limit scanning to this section only
    next_section = html_content.find('<section id=', section_start + len(section_marker))
    scan_end = next_section if next_section != -1 else len(html_content)

    # Find the first pub-item whose year < pub_year → insert before it
    year_tag = '<div class="pub-year">'
    item_tag = '<div class="pub-item">'
    insert_pos = None
    pos = after_open_tag

    try:
        new_year_int = int(pub_year) if pub_year else 0
    except ValueError:
        new_year_int = 0

    while pos < scan_end:
        year_div = html_content.find(year_tag, pos, scan_end)
        if year_div == -1:
            break
        year_close = html_content.find('</div>', year_div)
        if year_close == -1:
            break
        year_str = html_content[year_div + len(year_tag):year_close].strip()
        try:
            existing_year_int = int(year_str)
        except ValueError:
            pos = year_close + 1
            continue

        if existing_year_int < new_year_int:
            # Find the pub-item div that owns this year div
            item_div = html_content.rfind(item_tag, after_open_tag, year_div)
            if item_div != -1:
                insert_pos = item_div
            break

        pos = year_close + 1

    if insert_pos is None:
        # No older entry found — prepend at top of pub-list (skip the newline after the tag)
        insert_pos = after_open_tag
        if insert_pos < len(html_content) and html_content[insert_pos] == '\n':
            insert_pos += 1

    return (
        html_content[:insert_pos]
        + new_entry_html + "\n"
        + html_content[insert_pos:]
    )


def update_sidebar_counts(html_content):
    """
    Recount pub-items per section and update the sidebar meta labels.
    Handles both 'N publications' and 'N datasets' labels.
    """
    def count_items_in_section(content, section_id):
        marker = f'<section id="{section_id}">'
        start = content.find(marker)
        if start == -1:
            return 0
        next_sec = content.find('<section id=', start + len(marker))
        chunk = content[start:next_sec] if next_sec != -1 else content[start:]
        return chunk.count('<div class="pub-item">')

    n_articles = count_items_in_section(html_content, "journal-articles")
    n_datasets  = count_items_in_section(html_content, "datasets")

    # Replace sidebar meta text (handles any previous count)
    html_content = re.sub(
        r'(\d+)\s+publication(s?)',
        f'{n_articles} publication{"s" if n_articles != 1 else ""}',
        html_content
    )
    html_content = re.sub(
        r'(\d+)\s+dataset(s?)',
        f'{n_datasets} dataset{"s" if n_datasets != 1 else ""}',
        html_content
    )
    return html_content


def update_publications_html(new_pubs):
    """
    For each new publication, insert a formatted entry into the correct section
    of publications.html and update the sidebar counts.
    """
    if not os.path.exists(PUBS_HTML):
        print(f"  Warning: {PUBS_HTML} not found — skipping HTML update")
        return

    with open(PUBS_HTML) as f:
        html_content = f.read()

    for pub in new_pubs:
        section_id = get_section_id(pub.get("type", ""))
        entry_html = generate_pub_html_entry(pub)
        html_content = insert_pub_into_section(
            html_content, section_id, entry_html, pub.get("year", "")
        )
        print(f"  Inserted into #{section_id}: {pub['title'][:60]}...")

    html_content = update_sidebar_counts(html_content)

    with open(PUBS_HTML, "w") as f:
        f.write(html_content)
    print(f"Updated {PUBS_HTML}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Checking ORCID publications for {ORCID_ID}...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    orcid_data   = fetch_orcid_works()
    current_pubs = parse_works(orcid_data)
    print(f"Found {len(current_pubs)} publications on ORCID")

    existing_pubs = load_existing_publications()
    print(f"Found {len(existing_pubs)} existing publications in local database")

    new_pubs = find_new_publications(current_pubs, existing_pubs)

    if not new_pubs:
        print("No new publications found. Everything is up to date!")
        if not existing_pubs:
            save_publications(current_pubs)
        return

    print(f"\nFound {len(new_pubs)} NEW publication(s):")

    # Fetch full details (contributor list) for each new pub
    for pub in new_pubs:
        print(f"  - {pub['title']} ({pub['year']})")
        put_code = pub.get("put_code", "")
        if put_code:
            details = fetch_work_details(put_code)
            contributors = _extract_contributors(details)
            pub["authors_html"] = format_authors(contributors)
        else:
            pub["authors_html"] = ""

    # Update JSON
    save_publications(current_pubs)

    # Update HTML
    update_publications_html(new_pubs)

    # Write summary for the PR body
    summary_file = os.path.join(os.path.dirname(__file__), "update_summary.txt")
    with open(summary_file, "w") as f:
        f.write(f"Publication Update - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Found {len(new_pubs)} new publication(s):\n\n")
        for pub in new_pubs:
            f.write(f"- {pub['title']}\n")
            f.write(f"  Journal:  {pub['journal']}\n")
            f.write(f"  Year:     {pub['year']}\n")
            if pub.get("doi"):
                f.write(f"  DOI:      {pub['doi']}\n")
            f.write("\n")
    print(f"\nUpdate summary written to {summary_file}")
    print("A pull request will be created for review.")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"new_pubs=true\n")
            f.write(f"pub_count={len(new_pubs)}\n")


if __name__ == "__main__":
    main()
