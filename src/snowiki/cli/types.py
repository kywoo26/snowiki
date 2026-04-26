from __future__ import annotations

import re
from datetime import timedelta
from typing import override

import click

from snowiki.fileback.models import FILEBACK_PROPOSAL_ID_PATTERN


class DurationParamType(click.ParamType):
    """Parse compact duration strings such as 30d, 12h, or 60s."""

    name: str = "duration"

    @override
    def convert(
        self,
        value: object,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> timedelta:
        if isinstance(value, timedelta):
            return value
        if not isinstance(value, str):
            self.fail("duration must be a string", param, ctx)
        normalized = value.strip().lower()
        if not normalized:
            self.fail("duration must not be empty", param, ctx)
        unit = normalized[-1]
        amount_text = normalized[:-1]
        if not amount_text.isdigit() or unit not in {"d", "h", "s"}:
            self.fail("duration must use a positive integer plus d, h, or s", param, ctx)
        amount = int(amount_text)
        if amount <= 0:
            self.fail("duration must be positive", param, ctx)
        if unit == "d":
            return timedelta(days=amount)
        if unit == "h":
            return timedelta(hours=amount)
        return timedelta(seconds=amount)


DURATION = DurationParamType()


class ProposalIdParamType(click.ParamType):
    """Validate Snowiki fileback proposal identifiers at the CLI boundary."""

    name: str = "proposal-id"

    def __init__(self, pattern: re.Pattern[str]) -> None:
        self._pattern: re.Pattern[str] = pattern

    @override
    def convert(
        self,
        value: object,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> str:
        if not isinstance(value, str):
            self.fail("proposal id must be a string", param, ctx)
        if self._pattern.fullmatch(value) is None:
            self.fail(
                "proposal id must match fileback-proposal-<16 lowercase hex chars>",
                param,
                ctx,
            )
        return value


PROPOSAL_ID = ProposalIdParamType(FILEBACK_PROPOSAL_ID_PATTERN)
