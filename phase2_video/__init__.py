"""StraitWatch Phase 2A video-intelligence core.

The package is deliberately dependency-free.  Generative providers may write
scripts, but all selection, packaging and acceptance decisions remain local,
deterministic and auditable.
"""

from .package import build_video_package, load_site_inputs
from .rules import decide_video, load_rules
from .script import generate_local_script, generate_script
from .validator import validate_package, validate_script

__all__ = [
    "build_video_package",
    "decide_video",
    "generate_local_script",
    "generate_script",
    "load_rules",
    "load_site_inputs",
    "validate_package",
    "validate_script",
]
