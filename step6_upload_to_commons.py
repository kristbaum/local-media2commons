#!/usr/bin/env python3
"""
Step 6: Upload files to Wikimedia Commons
Downloads files from FürthWiki and uploads them to Commons with proper metadata.
"""

import csv
import requests
import os
import time
import hashlib
import re
from urllib.parse import urlparse, unquote
import mwclient
from datetime import datetime

# Configuration
INPUT_FILE = "step5_commons_ready.csv"
DOWNLOAD_DIR = "downloads"
LOG_FILE = "step6_upload_log.csv"

# Commons API configuration
COMMONS_SITE = "commons.wikimedia.org"
USER_AGENT = "FürthWiki-to-Commons-Bot/1.0 (https://github.com/kristbaum/local-media2commons)"

class CommonsUploader:
    def __init__(self, username=None, password=None):
        """Initialize the Commons uploader"""
        self.username = username
        self.password = password
        self.site = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
        # Create download directory
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # Initialize log file
        self.init_log_file()
    
    def init_log_file(self):
        """Initialize the upload log file"""
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'filename', 'status', 'commons_url', 'error_message'])
    
    def log_upload(self, filename, status, commons_url="", error_message=""):
        """Log upload attempt"""
        timestamp = datetime.now().isoformat()
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, filename, status, commons_url, error_message])
    
    def connect_to_commons(self):
        """Connect to Wikimedia Commons"""
        try:
            self.site = mwclient.Site(COMMONS_SITE, clients_useragent=USER_AGENT)
            
            if self.username and self.password:
                self.site.login(self.username, self.password)
                print(f"✅ Logged in to Commons as: {self.username}")
            else:
                print("⚠️  Not logged in - uploads will not work without authentication")
                return False
            
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Commons: {e}")
            return False
    
    def get_file_url_from_fuerthwiki(self, page_url, sha1_hash, filename):
        """Extract the actual file URL from a FürthWiki file page"""
        try:
            response = self.session.get(page_url)
            response.raise_for_status()
            
            content = response.text
            
            # Look for direct file URLs in the content - MediaWiki has predictable patterns
            patterns = [
                # Look for full-size image links (not thumbnails)
                r'href="(/wiki/images/[^/]+/[^/]+/[^"]*\.(jpg|jpeg|png|gif|pdf|svg))"(?![^"]*thumb)',
                r'src="(/wiki/images/[^/]+/[^/]+/[^"]*\.(jpg|jpeg|png|gif|pdf|svg))"(?![^"]*thumb)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_url = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                    
                    if file_url.startswith('/'):
                        file_url = f"https://www.fuerthwiki.de{file_url}"
                    
                    print(f"📁 Extracted file URL: {file_url}")
                    return file_url
            
            print(f"⚠️  Could not find direct file URL in page content")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting file URL from {page_url}: {e}")
            return None
    
    def download_file(self, file_url, filename, expected_sha1):
        """Download file from FürthWiki and verify its hash"""
        try:
            # Clean filename for local storage
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            local_path = os.path.join(DOWNLOAD_DIR, safe_filename)
            
            # Skip if already downloaded and verified
            if os.path.exists(local_path):
                if self.verify_file_hash(local_path, expected_sha1):
                    print(f"✅ File already downloaded and verified: {safe_filename}")
                    return local_path
                else:
                    print(f"🔄 Re-downloading file with incorrect hash: {safe_filename}")
            
            print(f"⬇️  Downloading: {filename}")
            response = self.session.get(file_url, stream=True)
            response.raise_for_status()
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r   Progress: {percent:.1f}%", end='')
            
            print()  # New line after progress
            
            # Verify hash
            if self.verify_file_hash(local_path, expected_sha1):
                print(f"✅ Download verified: {safe_filename}")
                return local_path
            else:
                print(f"❌ Hash verification failed for: {safe_filename}")
                os.remove(local_path)  # Remove corrupted file
                return None
                
        except Exception as e:
            print(f"❌ Download failed for {filename}: {e}")
            return None
    
    def verify_file_hash(self, file_path, expected_sha1):
        """Verify file SHA1 hash"""
        try:
            sha1_hash = hashlib.sha1()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha1_hash.update(chunk)
            
            actual_sha1 = sha1_hash.hexdigest()
            return actual_sha1.lower() == expected_sha1.lower()
        except Exception as e:
            print(f"❌ Hash verification error: {e}")
            return False
    
    def upload_to_commons(self, local_path, commons_filename, wikitext, comment="Uploaded from FürthWiki"):
        """Upload file to Wikimedia Commons"""
        try:
            if not self.site:
                raise Exception("Not connected to Commons")
            
            # Check if file already exists
            existing_page = self.site.pages[f"File:{commons_filename}"]
            if existing_page.exists:
                print(f"⚠️  File already exists on Commons: {commons_filename}")
                self.log_upload(commons_filename, "exists", f"https://commons.wikimedia.org/wiki/File:{commons_filename}")
                return False
            
            print(f"⬆️  Uploading to Commons: {commons_filename}")
            
            # Upload the file
            with open(local_path, 'rb') as f:
                result = self.site.upload(
                    file=f,
                    filename=commons_filename,
                    description=wikitext,
                    comment=comment
                )
            
            if result.get('result') == 'Success':
                commons_url = f"https://commons.wikimedia.org/wiki/File:{commons_filename}"
                print(f"✅ Upload successful: {commons_url}")
                self.log_upload(commons_filename, "success", commons_url)
                return True
            else:
                error_msg = str(result.get('warnings', result))
                print(f"❌ Upload failed: {error_msg}")
                self.log_upload(commons_filename, "failed", "", error_msg)
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Upload error for {commons_filename}: {error_msg}")
            self.log_upload(commons_filename, "error", "", error_msg)
            return False
    
    def process_file(self, row):
        """Process a single file from the CSV"""
        commons_filename = row['commons_filename']
        original_title = row['original_title']
        fuerthwiki_url = row['fuerthwiki_url']
        expected_sha1 = row['sha1']
        wikitext = row['wikitext']
        
        print(f"\n{'='*60}")
        print(f"Processing: {commons_filename}")
        print(f"{'='*60}")
        
        # Step 1: Get direct file URL from FürthWiki page
        file_url = self.get_file_url_from_fuerthwiki(fuerthwiki_url, expected_sha1, original_title)
        if not file_url:
            print(f"❌ Could not get file URL for: {commons_filename}")
            self.log_upload(commons_filename, "no_url", "", "Could not extract file URL")
            return False
        
        print(f"📁 File URL: {file_url}")
        
        # Step 2: Download file
        local_path = self.download_file(file_url, commons_filename, expected_sha1)
        if not local_path:
            print(f"❌ Download failed for: {commons_filename}")
            return False
        
        # Step 3: Upload to Commons
        success = self.upload_to_commons(local_path, commons_filename, wikitext)
        
        # Step 4: Clean up local file (optional - comment out to keep files)
        # os.remove(local_path)
        
        return success
    
    def run_batch_upload(self, max_files=None, start_from=0):
        """Run batch upload from CSV file"""
        if not self.connect_to_commons():
            return
        
        total_processed = 0
        successful_uploads = 0
        
        print(f"\n🚀 Starting batch upload from {INPUT_FILE}")
        print(f"📊 Will process files starting from row {start_from}")
        if max_files:
            print(f"📊 Maximum files to process: {max_files}")
        print(f"📁 Downloads will be saved to: {DOWNLOAD_DIR}")
        print(f"📝 Upload log: {LOG_FILE}")
        
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Skip to start position
                for i in range(start_from):
                    next(reader, None)
                
                for row in reader:
                    total_processed += 1
                    
                    try:
                        success = self.process_file(row)
                        if success:
                            successful_uploads += 1
                        
                        # Rate limiting - be nice to the servers
                        time.sleep(2)  # 2 second delay between uploads
                        
                        if max_files and total_processed >= max_files:
                            break
                            
                    except KeyboardInterrupt:
                        print("\n⚠️  Upload interrupted by user")
                        break
                    except Exception as e:
                        print(f"❌ Unexpected error processing file: {e}")
                        continue
        
        except FileNotFoundError:
            print(f"❌ Input file not found: {INPUT_FILE}")
            return
        
        print(f"\n{'='*60}")
        print("BATCH UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"Total files processed: {total_processed}")
        print(f"Successful uploads: {successful_uploads}")
        print(f"Failed uploads: {total_processed - successful_uploads}")
        print(f"Success rate: {(successful_uploads/total_processed*100):.1f}%" if total_processed > 0 else "0%")
        print(f"Log file: {LOG_FILE}")

def main():
    """Main function"""
    print("=" * 70)
    print("STEP 6: WIKIMEDIA COMMONS UPLOADER")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: This script requires:")
    print("   • Wikimedia Commons account with upload permissions")
    print("   • Bot password (recommended) or account password")
    print("   • Careful review of upload policies")
    print()
    
    # Get credentials
    username = input("Enter your Commons username (or press Enter to skip): ").strip()
    if username:
        password = input("Enter your password/bot password: ").strip()
    else:
        username = None
        password = None
        print("⚠️  Running in test mode - no uploads will be performed")
    
    # Initialize uploader
    uploader = CommonsUploader(username, password)
    
    if username:
        # Ask for upload parameters
        print("\nUpload options:")
        try:
            start_from = int(input("Start from row number (0 for beginning): ") or "0")
            max_files = input("Maximum files to upload (press Enter for all): ").strip()
            max_files = int(max_files) if max_files else None
        except ValueError:
            start_from = 0
            max_files = None
        
        # Confirm before starting
        print(f"\n🚨 READY TO UPLOAD:")
        print(f"   • Starting from row: {start_from}")
        print(f"   • Max files: {max_files or 'all remaining'}")
        print(f"   • Account: {username}")
        
        confirm = input("\nProceed with upload? (yes/no): ").strip().lower()
        if confirm == 'yes':
            uploader.run_batch_upload(max_files, start_from)
        else:
            print("Upload cancelled.")
    else:
        print("No credentials provided - upload cancelled.")

if __name__ == "__main__":
    main()
