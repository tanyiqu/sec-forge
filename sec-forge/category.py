from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class Category:
    name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    order: int = 0
