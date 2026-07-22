"""Central configuration: endpoints, paths and the file names each step reads/writes."""

from pathlib import Path

# Source wiki. Everything here is FürthWiki-specific and is the main thing to
# change when pointing the pipeline at another MediaWiki installation.
LOCAL_WIKI_API = "https://www.fuerthwiki.de/wiki/api.php"
LOCAL_WIKI_BASE = "https://www.fuerthwiki.de"
LOCAL_WIKI_FILE_PAGE = "https://www.fuerthwiki.de/wiki/index.php/{title}"

# Semantic MediaWiki properties fetched in step 3.
SMW_PROPERTIES = [
    "Beschreibung",
    "Erstellungsdatum",
    "Erstellungsjahr",
    "Lizenz",
    "Person",
    "Quellangaben",
    "Urheber",
]

# Target wiki.
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_SITE = "commons.wikimedia.org"
COMMONS_FILE_URL = "https://commons.wikimedia.org/wiki/File:{filename}"

USER_AGENT = (
    "FuerthWiki-to-Commons-Bot/1.0 (https://github.com/kristbaum/local-media2commons)"
)

# Categories added to every uploaded file.
COMMONS_CATEGORIES = ["Images from FürthWiki", "Media uploaded from FürthWiki ({year})"]

# Repository layout. Every step reads and writes inside DATA_DIR.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"

STEP1_RESULT = DATA_DIR / "step1_result.csv"
STEP2_RESULT = DATA_DIR / "step2_result.csv"
STEP3_RESULT = DATA_DIR / "step3_result.csv"
STEP3_REPORT = DATA_DIR / "step3_report.txt"
STEP4_RESULT = DATA_DIR / "step4_commons_ready.csv"
STEP5_LOG = DATA_DIR / "step5_upload_log.csv"
