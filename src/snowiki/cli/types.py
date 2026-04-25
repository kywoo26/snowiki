from __future__ import annotations

from datetime import timedelta

import click


class DurationParamType(click.ParamType):
    """Parse compact duration strings such as 30d, 12h, or 60s."""

    name = "duration"

    def convert(
        self,
        value: object,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> timedelta:
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
