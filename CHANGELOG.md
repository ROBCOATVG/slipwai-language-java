# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.0.0

**Java is now a language family package of its own.** What both Java backends that were built into slipwai
share — Maven's toolchain and wrapper, the analyser configuration, the source layout and package rename, the
event-store and read-model adapters, the flag reader, the pruner's rows and the example snippets — lives here,
with the history it had there. It owns no backend: `java-quarkus` and `java-spring` are framework packages that
require it (`requires: {"java": ">=1.0,<2"}`), and `language.json` names `quarkus` as the framework `--language java`
defaults to. slipwai loads it from its language directory (`$SLIPWAI_LANGUAGES`, or `~/.slipwai/languages`), and the
projects it generates are byte for byte those slipwai generated with Java built in. It declares the catalog schema
it loads on, `core >=9.0,<10`.

