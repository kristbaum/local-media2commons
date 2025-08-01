# Local-Media-2-Commons

A script to sync local MediaWiki media files to Wikimedia Commons.  
Initially, this will be used to transfer media files from FürthWiki.  

The goal is to make this process repeatable, enabling repeatable imports.

---

## Methodology

1. **Get a list of all files in the local MediaWiki installation**  
   This can be done in various ways depending on your local MediaWiki setup.

2. **Extract the SHA1 hash of each file**  
   Implemented in: `step2_get_allimagehashes.py`

3. **Check if the file already exists on Wikimedia Commons**  
   Implemented in: `step3_check_if_file_exists_on_commons.py`

4. **Extract file metadata from the local MediaWiki**  
   Focus on using the Semantic MediaWiki API with ASK queries.  
   Implemented in: `step4_extract_metadata.py`

5. **Transform the saved metadata**  
   Convert metadata into a format usable by OpenRefine for uploading.

6. **Upload files to Wikimedia Commons**  
   Use OpenRefine for batch uploads.

---

## Example: Check if SHA1 hash exists on Wikimedia Commons

```bash
https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aisha1=fcdfc17fac0c39e6f201f2022f9f1f9f8b35d449&format=json
```

## Template to modify metadata into

```
=={{int:filedesc}}==
{{Information}}

=={{int:license-header}}==
{{self|CC-BY-SA-4.0}} <!-- make sure to adjust to the correct license template, even if you also provide copyright and license info in the structured data–->

[[Category:Your category 1]]
[[Category:Your category 2]]
```
