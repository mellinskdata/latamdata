"""Backward-compatible imports for older Streamlit deployments.

The analytics engine now lives in scout_analytics.py. Keeping this module
prevents older app revisions that still import analytics from crashing during
a rolling Streamlit Cloud redeploy.
"""

from scout_analytics import *  # noqa: F401,F403
