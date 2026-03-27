"""
WhiteNoise: Django ``STATIC_ROOT`` and related static files.

Per-item Docusaurus builds are served by :func:`accessdoc.views.serve_publish_build`.
"""

from __future__ import annotations

from whitenoise.middleware import WhiteNoiseMiddleware


class AccessDocWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """Same as ``WhiteNoiseMiddleware`` — doc sites use the viewer view, not extra roots."""
