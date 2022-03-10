import logging
import os

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(format="%(levelname)s: %(message)s", level=LOGLEVEL)
