from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import SnowikiReadOnlyFacade

RESOURCE_SCHEME = "session://"


def build_resource(facade: SnowikiReadOnlyFacade, session_id: str) -> dict[str, object]:
    return facade.session_resource(session_id)
