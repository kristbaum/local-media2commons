import csv
import requests
import json

# Files
INPUT_FILE = "step3_result.csv"
OUTPUT_FILE = "step4_result.csv"
API_ENDPOINT = "https://www.fuerthwiki.de/wiki/api.php"

# SMW properties to extract
properties = ["Beschreibung", "Erstellungsdatum", "Erstellungsjahr", "Lizenz", "Person", "Quellangaben", "Urheber"]

# Step 1: Read input CSV into a dict keyed by title
input_rows = []
title_to_row = {}

with open(INPUT_FILE, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        title = row["title"]
        input_rows.append(row)
        title_to_row[title] = row

# Step 2: Chunk titles for SMW querying
def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

# Step 3: Query SMW for each chunk
results_all = []
for chunk in chunked(list(title_to_row.keys()), 10): # Conservative chunk size
    page_filters = " OR ".join(f"[[{title}]]" for title in chunk)
    property_selectors = "".join(f"|?{prop}" for prop in properties)
    ask_query = f"{page_filters}{property_selectors}"
    print(ask_query)

    params = {
        "action": "ask",
        "query": ask_query,
        "format": "json"
    }
    response = requests.get(API_ENDPOINT, params=params)
    response.raise_for_status()
    data = response.json()

    results = data.get("query", {}).get("results", {})
    for title, entry in results.items():
        # Start with the original row
        base_row = title_to_row.get(title, {}).copy()
        for prop in properties:
            values = entry.get("printouts", {}).get(prop, [])
            base_row[prop] = "; ".join(str(v) for v in values)
        results_all.append(base_row)
    break

# Step 4: Determine output columns
original_fields = list(input_rows[0].keys())
fieldnames = original_fields + [p for p in properties if p not in original_fields]

# Step 5: Write to output CSV
with open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results_all)

print(f"Saved {len(results_all)} rows to {OUTPUT_FILE}")
