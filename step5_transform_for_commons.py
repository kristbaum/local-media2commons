#!/usr/bin/env python3
"""
Step 5: Transform data for Commons compatibility
Filters step4_result.csv to only Commons-compatible licenses and generates wikitext for uploads.
"""

import csv
import re
from datetime import datetime

# Files
INPUT_FILE = "step4_result.csv"
OUTPUT_FILE = "step5_commons_ready.csv"

def clean_license_value(license_value):
    """Clean and normalize license values"""
    if not license_value or license_value.strip() == "":
        return None
    
    license_value = license_value.strip()
    
    # Remove HTML markup and wiki markup
    license_value = re.sub(r'<[^>]+>', '', license_value)  # Remove HTML tags
    license_value = re.sub(r'\[\[[^\]]+\]\]', '', license_value)  # Remove wiki links
    license_value = re.sub(r'\{\|.*?\|\}', '', license_value, flags=re.DOTALL)  # Remove wiki tables
    license_value = re.sub(r'\s+', ' ', license_value).strip()  # Normalize whitespace
    
    # Extract license from common patterns
    cc_pattern = r'(cc-by(?:-sa|-nc|-nd)*-?\d*\.?\d*)'
    cc_match = re.search(cc_pattern, license_value.lower())
    if cc_match:
        license_value = cc_match.group(1)
    
    # Handle common variations and return standardized format
    license_mappings = {
        "cc-by-sa-3.0": "CC-BY-SA-3.0",
        "cc-by-sa-4.0": "CC-BY-SA-4.0",
        "cc-by-sa-3": "CC-BY-SA-3.0",
        "cc-by-3.0": "CC-BY-3.0",
        "cc-by-4.0": "CC-BY-4.0",
        "public domain": "PD",
        "pd": "PD",
        "pdm": "PD",
        "pd-alt": "PD",
        "gemeinfrei": "PD",
        "gfdl": "GFDL"
    }
    
    return license_mappings.get(license_value.lower())

def is_commons_compatible_license(license_name):
    """Check if a license is compatible with Wikimedia Commons"""
    if not license_name:
        return False
    compatible_licenses = ["CC-BY-SA-3.0", "CC-BY-SA-4.0", "CC-BY-3.0", "CC-BY-4.0", "PD", "GFDL"]
    return license_name in compatible_licenses

def get_license_template(license_name):
    """Get the appropriate Commons license template"""
    template_mappings = {
        "CC-BY-SA-3.0": "{{self|CC-BY-SA-3.0}}",
        "CC-BY-SA-4.0": "{{self|CC-BY-SA-4.0}}",
        "CC-BY-3.0": "{{self|CC-BY-3.0}}",
        "CC-BY-4.0": "{{self|CC-BY-4.0}}",
        "PD": "{{PD-self}}",
        "GFDL": "{{self|GFDL}}"
    }
    return template_mappings.get(license_name, "{{self|CC-BY-SA-3.0}}")

def clean_filename(filename):
    """Clean filename for Commons (remove 'Datei:' prefix)"""
    if filename.startswith('Datei:'):
        return filename[6:]  # Remove 'Datei:' prefix
    return filename

def clean_description(description):
    """Clean and format description for Commons"""
    if not description:
        return ""
    
    # Remove wiki markup that might not work on Commons
    description = re.sub(r'\[\[([^|\]]+)\|([^]]+)\]\]', r'\2', description)  # [[link|text]] -> text
    description = re.sub(r'\[\[([^]]+)\]\]', r'\1', description)  # [[link]] -> link
    description = description.replace('""', '"')  # Fix double quotes
    
    return description.strip()

def clean_author(author):
    """Clean author information"""
    if not author:
        return ""
    
    # Remove wiki markup
    author = re.sub(r'\[\[([^|\]]+)\|([^]]+)\]\]', r'\2', author)  # [[link|text]] -> text
    author = re.sub(r'\[\[([^]]+)\]\]', r'\1', author)  # [[link]] -> link
    author = author.replace('Benutzer:', '').replace('[[', '').replace(']]', '')
    
    return author.strip()

def clean_source(source):
    """Clean source information"""
    if not source:
        return ""
    
    # Remove wiki markup
    source = re.sub(r'\[\[([^|\]]+)\|([^]]+)\]\]', r'\2', source)  # [[link|text]] -> text
    source = re.sub(r'\[\[([^]]+)\]\]', r'\1', source)  # [[link]] -> link
    
    return source.strip()

def extract_year(date_str):
    """Extract year from date string"""
    if not date_str:
        return ""
    
    # Try to extract 4-digit year
    year_match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
    if year_match:
        return year_match.group()
    
    return ""

def generate_wikitext(row, license_name):
    """Generate Commons wikitext for a file"""
    
    filename = clean_filename(row['title'])
    description = clean_description(row['Beschreibung'])
    author = clean_author(row['Urheber'])
    source = clean_source(row['Quellangaben'])
    date = extract_year(row['Erstellungsdatum'])
    license_template = get_license_template(license_name)
    original_url = row['url']
    
    # Build the Information template
    info_template = "{{Information\n"
    info_template += f"|description={{{{de|1={description}}}}}\n"
    
    if date:
        info_template += f"|date={date}\n"
    else:
        info_template += "|date=\n"
    
    if source:
        info_template += f"|source=[{original_url} FürthWiki] - {source}\n"
    else:
        info_template += f"|source=[{original_url} FürthWiki]\n"
    
    if author:
        info_template += f"|author={author}\n"
    else:
        info_template += "|author=\n"
    
    info_template += "|permission=\n"
    info_template += "|other_versions=\n"
    info_template += "}}"
    
    # Complete wikitext
    wikitext = f"""=={{{{int:filedesc}}}}==
{info_template}

=={{{{int:license-header}}}}==
{license_template}

[[Category:Images from FürthWiki]]
[[Category:Media uploaded from FürthWiki ({datetime.now().year})]]"""

    return wikitext

def main():
    """Main function to process the CSV and generate Commons-ready data"""
    
    compatible_count = 0
    total_count = 0
    output_rows = []
    
    # Process input CSV
    with open(INPUT_FILE, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            total_count += 1
            
            # Skip files that already exist on Commons
            if row['exists_on_commons'].lower() == 'true':
                continue
            
            # Clean and check license
            license_name = clean_license_value(row['Lizenz'])
            
            if is_commons_compatible_license(license_name):
                compatible_count += 1
                
                # Generate wikitext
                wikitext = generate_wikitext(row, license_name)
                
                # Create output row with only necessary columns
                output_row = {
                    'commons_filename': clean_filename(row['title']),
                    'original_title': row['title'],
                    'sha1': row['sha1'],
                    'fuerthwiki_url': row['url'],
                    'description': clean_description(row['Beschreibung']),
                    'date': extract_year(row['Erstellungsdatum']),
                    'author': clean_author(row['Urheber']),
                    'source': clean_source(row['Quellangaben']),
                    'license': license_name,
                    'wikitext': wikitext
                }
                
                output_rows.append(output_row)
    
    # Write output CSV
    if output_rows:
        fieldnames = ['commons_filename', 'original_title', 'sha1', 'fuerthwiki_url', 
                     'description', 'date', 'author', 'source', 'license', 'wikitext']
        
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
    
    # Print summary
    print("=" * 60)
    print("STEP 5: COMMONS TRANSFORMATION COMPLETE")
    print("=" * 60)
    print(f"Total files processed: {total_count:,}")
    print(f"Commons-compatible files: {compatible_count:,}")
    print(f"Files ready for upload: {len(output_rows):,}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print()
    
    # Show license breakdown
    license_counts = {}
    for row in output_rows:
        license = row['license']
        license_counts[license] = license_counts.get(license, 0) + 1
    
    print("License distribution in output:")
    for license, count in sorted(license_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {license}: {count:,}")
    print()
    
    # Show sample wikitext
    if output_rows:
        print("Sample wikitext for first file:")
        print("-" * 40)
        print(f"File: {output_rows[0]['commons_filename']}")
        print()
        print(output_rows[0]['wikitext'][:500] + "..." if len(output_rows[0]['wikitext']) > 500 else output_rows[0]['wikitext'])

if __name__ == "__main__":
    main()
