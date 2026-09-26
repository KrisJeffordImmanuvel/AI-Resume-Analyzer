"""Small text helpers shared by the analysis modules."""

import re

# A bullet point: "-", "*", "•" and similar marks, or a number such as "1." or "2)", then a space.
BULLET = re.compile(r"^\s*(?:[-*•·▪◦‣–]|\d+[.)])\s+")


def is_bullet(line: str) -> bool:
    return bool(BULLET.match(line))


def strip_bullet(line: str) -> str:
    return BULLET.sub("", line, count=1).strip()
