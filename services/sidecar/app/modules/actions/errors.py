"""The one error type every action raises when a proposal can't run."""


class ActionError(Exception):
    """A proposal that can't run (unknown exercise, food or program, no profile...)."""
