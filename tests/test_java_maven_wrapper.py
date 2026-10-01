"""The Maven wrapper this family ships into every generated Java project keeps the bytes it needs.

`mvnw` is a POSIX shell script and `mvnw.cmd` a batch/PowerShell polyglot that re-reads itself, so their line
endings are load-bearing; `.gitattributes` at this package's root declares them, and a checkout that lost it would
ship a wrapper one of the two platforms cannot run. Read from this package's own tree, as a checkout has it.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "assets/languages/java/build"


class MavenWrapperTest(unittest.TestCase):
    def test_mvnw_is_lf_and_mvnw_cmd_is_crlf_throughout(self) -> None:
        shell = (BUILD / "mvnw").read_bytes()
        batch = (BUILD / "mvnw.cmd").read_bytes()
        self.assertNotIn(b"\r", shell)
        lines = batch.split(b"\n")[:-1]
        self.assertTrue(lines)
        self.assertTrue(all(line.endswith(b"\r") for line in lines), "every line of mvnw.cmd ends in CRLF")

    def test_the_wrapper_pins_one_maven_release(self) -> None:
        properties = (BUILD / ".mvn/wrapper/maven-wrapper.properties").read_text()
        self.assertRegex(properties, r"apache-maven-\d+\.\d+\.\d+-bin\.zip")
        self.assertIsNotNone(re.search(r"(?m)^distributionType=only-script$", properties))


if __name__ == "__main__":
    unittest.main()
