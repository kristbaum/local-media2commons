#!/usr/bin/env python3
"""
Improved analysis script for step4_result.csv
Generates a comprehensive report on the media files data with better license parsing.
"""

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

# Input file
INPUT_FILE = "step4_result.csv"

def clean_license_value(license_value):
    """Clean and normalize license values with better parsing"""
    if not license_value or license_value.strip() == "":
        return "No license specified"
    
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
    
    # Handle common variations
    license_mappings = {
        "cc-by-sa-3.0": "CC-BY-SA-3.0",
        "cc-by-sa-4.0": "CC-BY-SA-4.0",
        "cc-by-sa-3": "CC-BY-SA-3.0",
        "cc-by-3.0": "CC-BY-3.0",
        "cc-by-4.0": "CC-BY-4.0", 
        "cc-by-nc-3.0": "CC-BY-NC-3.0",
        "cc-by-nc-4.0": "CC-BY-NC-4.0",
        "cc-by-nc-sa-3.0": "CC-BY-NC-SA-3.0",
        "cc-by-nc-sa-4.0": "CC-BY-NC-SA-4.0",
        "cc-by-nc-nd-3.0": "CC-BY-NC-ND-3.0",
        "cc-by-nc-nd-4.0": "CC-BY-NC-ND-4.0",
        "cc-by-nd-4.0": "CC-BY-ND-4.0",
        "copyright": "Copyright",
        "public domain": "Public Domain",
        "pd": "Public Domain",
        "pdm": "Public Domain",
        "pd-alt": "Public Domain",
        "gemeinfrei": "Public Domain",
        "gfdl": "GFDL",
        "bildlizenz-stadtarchiv": "Stadtarchiv License",
        "bildlizenz-yadvashem": "Yad Vashem License", 
        "bildlizenz-jmf": "JMF License",
        "noc-nc-1.0": "NOC-NC-1.0",
        "out of copyright - non commercial re-use": "Out of copyright (non-commercial)",
        "non-commercial use only": "Non-commercial only",
        "non-commercial usw only": "Non-commercial only"
    }
    
    # First try exact match
    normalized = license_mappings.get(license_value.lower(), license_value)
    
    # If still messy, try to extract meaningful parts
    if len(normalized) > 50 or '{' in normalized or 'cellspacing' in normalized:
        # Try to find CC license in the mess
        for pattern in ["cc-by-sa-3.0", "cc-by-sa-4.0", "cc-by-nc", "copyright"]:
            if pattern in normalized.lower():
                return license_mappings.get(pattern, "Unrecognized license")
        return "Malformed license data"
    
    return normalized

def extract_year_from_creation_date(date_str):
    """Extract year from various date formats"""
    if not date_str or date_str.strip() == "":
        return None
    
    date_str = date_str.strip()
    
    # Try to extract year from different formats
    if date_str.isdigit() and len(date_str) == 4:
        return int(date_str)
    
    # Handle YYYY-MM-DD format
    if "-" in date_str:
        try:
            year = int(date_str.split("-")[0])
            if 1800 <= year <= 2030:  # Reasonable year range
                return year
        except:
            pass
    
    # Try to find 4-digit year in the string
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        return int(year_match.group())
    
    return None

def is_commons_compatible_license(license_name):
    """Check if a license is compatible with Wikimedia Commons"""
    compatible_licenses = [
        "CC-BY-SA-3.0", "CC-BY-SA-4.0", "CC-BY-3.0", "CC-BY-4.0",
        "Public Domain", "GFDL"
    ]
    return license_name in compatible_licenses

def analyze_csv():
    """Main analysis function"""
    
    # Counters and data structures
    total_images = 0
    exists_on_commons = 0
    license_counter = Counter()
    year_counter = Counter()
    has_description = 0
    has_author = 0
    has_source = 0
    decade_counter = Counter()
    
    # Read and analyze the CSV
    with open(INPUT_FILE, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            total_images += 1
            
            # Check if exists on commons
            if row['exists_on_commons'].lower() == 'true':
                exists_on_commons += 1
            
            # Analyze licenses
            license_value = clean_license_value(row['Lizenz'])
            license_counter[license_value] += 1
            
            # Analyze creation years
            year = extract_year_from_creation_date(row['Erstellungsdatum'])
            if year:
                year_counter[year] += 1
                decade = (year // 10) * 10
                decade_counter[decade] += 1
            
            # Check metadata completeness
            if row['Beschreibung'].strip():
                has_description += 1
            
            if row['Urheber'].strip():
                has_author += 1
                
            if row['Quellangaben'].strip():
                has_source += 1
    
    return {
        'total_images': total_images,
        'exists_on_commons': exists_on_commons,
        'license_counter': license_counter,
        'year_counter': year_counter,
        'decade_counter': decade_counter,
        'has_description': has_description,
        'has_author': has_author,
        'has_source': has_source
    }

def generate_report(data):
    """Generate and print the analysis report"""
    
    print("=" * 70)
    print("FÜRTHWIKI MEDIA ANALYSIS REPORT")
    print("=" * 70)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Basic statistics
    print("📊 BASIC STATISTICS")
    print("-" * 40)
    print(f"Total images analyzed: {data['total_images']:,}")
    print(f"Already exist on Commons: {data['exists_on_commons']:,} ({data['exists_on_commons']/data['total_images']*100:.1f}%)")
    print(f"Not on Commons: {data['total_images'] - data['exists_on_commons']:,} ({(data['total_images'] - data['exists_on_commons'])/data['total_images']*100:.1f}%)")
    print()
    
    # License distribution (top 15 only)
    print("📋 LICENSE DISTRIBUTION (Top 15)")
    print("-" * 40)
    commons_compatible_count = 0
    for i, (license_name, count) in enumerate(data['license_counter'].most_common(15)):
        percentage = count / data['total_images'] * 100
        compatible = "✓" if is_commons_compatible_license(license_name) else "✗"
        if is_commons_compatible_license(license_name):
            commons_compatible_count += count
        print(f"{compatible} {license_name}: {count:,} ({percentage:.1f}%)")
    
    # Show remaining licenses count
    remaining_licenses = len(data['license_counter']) - 15
    if remaining_licenses > 0:
        remaining_count = sum(count for license, count in data['license_counter'].most_common()[15:])
        print(f"   ... and {remaining_licenses} other licenses: {remaining_count:,}")
    print()
    
    # Metadata completeness
    print("📝 METADATA COMPLETENESS")
    print("-" * 40)
    desc_pct = data['has_description'] / data['total_images'] * 100
    author_pct = data['has_author'] / data['total_images'] * 100
    source_pct = data['has_source'] / data['total_images'] * 100
    
    print(f"Images with description: {data['has_description']:,} ({desc_pct:.1f}%)")
    print(f"Images with author info: {data['has_author']:,} ({author_pct:.1f}%)")
    print(f"Images with source info: {data['has_source']:,} ({source_pct:.1f}%)")
    print()
    
    # Year distribution (top 10)
    print("📅 CREATION YEAR DISTRIBUTION (Top 10)")
    print("-" * 40)
    years_with_data = sum(data['year_counter'].values())
    print(f"Images with year data: {years_with_data:,} ({years_with_data/data['total_images']*100:.1f}%)")
    print()
    
    for year, count in data['year_counter'].most_common(10):
        percentage = count / data['total_images'] * 100
        print(f"{year}: {count:,} ({percentage:.1f}%)")
    print()
    
    # Decade distribution
    print("📅 CREATION BY DECADE")
    print("-" * 40)
    for decade in sorted(data['decade_counter'].keys(), reverse=True)[:10]:
        count = data['decade_counter'][decade]
        percentage = count / data['total_images'] * 100
        print(f"{decade}s: {count:,} ({percentage:.1f}%)")
    print()
    
    # Commons upload potential
    print("🚀 COMMONS UPLOAD POTENTIAL")
    print("-" * 40)
    not_on_commons = data['total_images'] - data['exists_on_commons']
    
    print(f"Images with Commons-compatible licenses: {commons_compatible_count:,} ({commons_compatible_count/data['total_images']*100:.1f}%)")
    print(f"Images not yet on Commons: {not_on_commons:,} ({not_on_commons/data['total_images']*100:.1f}%)")
    print(f"Potential Commons uploads: ~{min(commons_compatible_count, not_on_commons):,} images")
    print("(Estimated based on license compatibility)")
    print()
    
    # Summary recommendations
    print("💡 KEY INSIGHTS & RECOMMENDATIONS")
    print("-" * 40)
    
    # License insights
    cc_by_sa_count = data['license_counter'].get('CC-BY-SA-3.0', 0) + data['license_counter'].get('CC-BY-SA-4.0', 0)
    copyright_count = data['license_counter'].get('Copyright', 0)
    no_license_count = data['license_counter'].get('No license specified', 0)
    
    print(f"• {cc_by_sa_count:,} images ({cc_by_sa_count/data['total_images']*100:.1f}%) are CC-BY-SA licensed - excellent for Commons!")
    
    if copyright_count > 0:
        print(f"• {copyright_count:,} images ({copyright_count/data['total_images']*100:.1f}%) have copyright restrictions")
    
    if no_license_count > 0:
        print(f"• {no_license_count:,} images lack license information")
    
    # Metadata insights
    if desc_pct > 95:
        print("• Excellent description coverage!")
    elif desc_pct < 80:
        print("• Consider improving description completeness")
    
    if author_pct > 80:
        print("• Good author attribution coverage")
    else:
        print("• Author information could be improved")
    
    # Year insights
    recent_images = sum(count for year, count in data['year_counter'].items() if year >= 2020)
    if recent_images > 0:
        print(f"• {recent_images:,} images from 2020+ show active documentation")
    
    print("• Focus on CC-BY-SA content for immediate Commons uploads")
    print("• Review copyright status for proprietary content")
    print()

if __name__ == "__main__":
    try:
        print("Analyzing step4_result.csv...")
        data = analyze_csv()
        generate_report(data)
        
        # Save clean summary to file
        summary_file = "step4_clean_analysis_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"FürthWiki Media Analysis Summary\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total images: {data['total_images']:,}\n")
            f.write(f"On Commons: {data['exists_on_commons']:,}\n")
            f.write(f"Not on Commons: {data['total_images'] - data['exists_on_commons']:,}\n\n")
            f.write("Top 10 License distribution:\n")
            for license_name, count in data['license_counter'].most_common(10):
                pct = count / data['total_images'] * 100
                compatible = "✓" if is_commons_compatible_license(license_name) else "✗"
                f.write(f"  {compatible} {license_name}: {count:,} ({pct:.1f}%)\n")
            
            f.write(f"\nMetadata completeness:\n")
            f.write(f"  Description: {data['has_description']:,} ({data['has_description']/data['total_images']*100:.1f}%)\n")
            f.write(f"  Author: {data['has_author']:,} ({data['has_author']/data['total_images']*100:.1f}%)\n")
            f.write(f"  Source: {data['has_source']:,} ({data['has_source']/data['total_images']*100:.1f}%)\n")
        
        print(f"Clean summary saved to: {summary_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}")
        print("Make sure the file exists in the current directory.")
    except Exception as e:
        print(f"Error analyzing file: {e}")
