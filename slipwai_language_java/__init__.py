"""The `java` language package: the Java family slipwai loads from its language directory.

`LANGUAGE` is the object core's loader reads: the `java` family, with no backend of its own (the bare name is kept
for a backend nothing owns the startup of, and every Java backend here has a framework). Its answers — Maven's
toolchain, the source layout and rename, the flag reader, the pruner's rows — are what `java-quarkus` and
`java-spring` inherit, and the files they read are the ones under `assets/` beside it.
"""
from __future__ import annotations

from .java import LANGUAGE

__all__ = ["LANGUAGE"]
