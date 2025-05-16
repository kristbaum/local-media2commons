# Local-Media-2-Commons

A script to sync local MediaWiki media files to Wikimedia Commons.
This will be used to tranfer media files from FürthWiki initially.
The plan is to make this process repeatable, to allow for continuous imports.

## Metodology

1. Get a list of all files in the local MediaWiki installation (This can be done multiple ways, depending on the setup of the local MediaWiki)
2. Extract the sha1 hash of each file -> implemented in step2_get_allimagehashes.py
3. Check if the file is already in Wikimedia Commons -> implemented in step3_check_if_file_exists_on_commons.py
4. Extract file and metadata from local MediaWiki. We will extract them focussing on the SemanticMediaWiki API
5. Upload file to Wikimedia Commons

## 3. Check SHA1 is in Wikimedia Commons

```bash
https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aisha1=fcdfc17fac0c39e6f201f2022f9f1f9f8b35d449&format=json
```

Ratelimit after 36680 rows in 12274.78 seconds. (over 3 hours)
