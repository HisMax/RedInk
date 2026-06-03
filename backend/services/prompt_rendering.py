"""
Prompt template rendering helpers.
"""

from __future__ import annotations

import re
from typing import Mapping


def render_prompt_template(template: str, values: Mapping[str, str]) -> str:
    """Replace known prompt placeholders while preserving literal JSON braces."""
    pattern = re.compile(r"\{(" + "|".join(re.escape(key) for key in values.keys()) + r")\}")
    return pattern.sub(lambda match: values[match.group(1)], template)
