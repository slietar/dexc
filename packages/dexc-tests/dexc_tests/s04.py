import logging

import dexc.autoinstall


def a():
  raise RuntimeError("A")

try:
  a()
except Exception as exc:
  e = exc
else:
  raise RuntimeError("B")

logger = logging.getLogger("dexc_tests.s04")
logger.error("An error", exc_info=(type(e), e, e.__traceback__))
