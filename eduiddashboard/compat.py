import sys

PY3 = sys.version_info[0] == 3

if PY3:  # pragma: no cover
    text_type = str
else:  # pragma: no cover
    text_type = unicode


if PY3:  # pragma: no cover
    from urllib import parse as urlparse

else:  # pragma: no cover
    import urlparse
