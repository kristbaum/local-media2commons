"""Central configuration: endpoints, paths and the file names each step reads/writes."""

from pathlib import Path

# Source wiki. Everything here is FürthWiki-specific and is the main thing to
# change when pointing the pipeline at another MediaWiki installation.
LOCAL_WIKI_API = "https://www.fuerthwiki.de/wiki/api.php"
LOCAL_WIKI_BASE = "https://www.fuerthwiki.de"
LOCAL_WIKI_FILE_PAGE = "https://www.fuerthwiki.de/wiki/index.php/{title}"

# Semantic MediaWiki properties recording what the source wiki already considers
# transferred. Read in step 1, next to the file list itself, and written back by
# step 2b.
SMW_COMMONS_PROPERTIES = ["UploadCommons", "CommonsLink"]
UPLOAD_COMMONS_PROPERTY, COMMONS_LINK_PROPERTY = SMW_COMMONS_PROPERTIES

# File pages carry their metadata as parameters of one form template, so that is
# where step 2b writes. Every media type has its own; a page whose first
# template is none of these is left alone.
FORM_TEMPLATES = ["Bild", "Audio", "Video"]

# The source wiki spells Semantic MediaWiki booleans in German.
SMW_TRUE = "Ja"

# The column step 2 writes: the Commons file page holding the identical bytes,
# empty when there is none. Result files written before it held a URL called it
# `exists_on_commons` and put `True`/`False` there; both are still read.
COMMONS_URL_FIELD = "commons_url"
LEGACY_COMMONS_URL_FIELD = "exists_on_commons"

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

# Wikimedia requires a User-Agent naming the tool and a way to contact whoever
# runs it (a URL or an e-mail); requests without one are throttled hardest.
# See https://meta.wikimedia.org/wiki/User-Agent_policy.
USER_AGENT = (
    "FuerthWiki-to-Commons-Bot/1.0 (https://github.com/kristbaum/local-media2commons)"
)

# Wikimedia's API rate limits, in requests per minute: a bot identified only by
# its User-Agent gets 200, an authenticated established account 2,000.
# See https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits.
ANONYMOUS_RATE_LIMIT = 200
AUTHENTICATED_RATE_LIMIT = 2000

# Delay between Commons requests in step 2, kept a good margin under those
# limits: 2/s anonymous, 10/s once logged in.
ANONYMOUS_DELAY = 0.5
AUTHENTICATED_DELAY = 0.1

# Categories added to every uploaded file.
COMMONS_CATEGORIES = ["Images from FürthWiki", "Media uploaded from FürthWiki ({year})"]

# Repository layout. Every step reads and writes inside DATA_DIR.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"

STEP1_RESULT = DATA_DIR / "step1_result.csv"
STEP2_RESULT = DATA_DIR / "step2_result.csv"
STEP2B_LOG = DATA_DIR / "step2b_update_log.csv"
STEP3_RESULT = DATA_DIR / "step3_result.csv"
STEP3_REPORT = DATA_DIR / "step3_report.txt"
STEP4_RESULT = DATA_DIR / "step4_commons_ready.csv"
STEP5_LOG = DATA_DIR / "step5_upload_log.csv"
