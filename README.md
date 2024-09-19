# Local-Media-2-Commons

A script to sync local MediaWiki media files to Wikimedia Commons.

# Metodology

1. Get a list of all files in the local MediaWiki installation
2. Extract the sha1 hash of each file -> get_allimagehashes.py
3. Check if the file is already in Wikimedia Commons -> check_if_file_exists_on_commons.py
4. Extract file and metadata from local MediaWiki
5. Upload file to Wikimedia Commons



## 3. Check SHA1 is in Wikimedia Commons

```bash
https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aisha1=fcdfc17fac0c39e6f201f2022f9f1f9f8b35d449&format=json
```