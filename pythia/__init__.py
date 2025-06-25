__license__ = "BSD-3-Clause"

import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
