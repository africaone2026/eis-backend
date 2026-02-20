from .base import *

# Determine which settings to load based on environment
try:
    from .development import *
except ImportError:
    pass
