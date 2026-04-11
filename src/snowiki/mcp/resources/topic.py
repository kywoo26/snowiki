from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import SnowikiReadOnlyFacade

RESOURCE_SCHEME = "topic://"


def build_resource(facade: SnowikiReadOnlyFacade, topic_slug: str) -> dict[str, object]:
    return facade.topic_resource(topic_slug)
