"""Retired legacy service ABC boundary.

Service orchestration now receives explicit dependencies at construction time. Domain
driver contracts live in ``core.interfaces.driver`` and concrete service types are
only referenced by the composition container for static typing.
"""

__all__: list[str] = []
