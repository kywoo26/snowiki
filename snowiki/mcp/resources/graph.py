from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import SnowikiReadOnlyFacade

RESOURCE_URI = "graph://current"


def build_resource(facade: SnowikiReadOnlyFacade) -> dict[str, object]:
    return facade.graph_resource()
