# SQLScope — Claude Context

## What This Project Is
An IntelliJ/PhpStorm plugin (Kotlin) that adds a right-click context menu in the
Project View to quickly assign SQL dialects and data source resolution scopes to
directories, replacing the tedious Settings → Languages & Frameworks → SQL Dialects flow.

## Build & Run

```bash
./gradlew buildPlugin      # produces build/distributions/SQLScope-1.0.0.zip
./gradlew runIde           # launches a sandboxed PhpStorm/IntelliJ for live testing
./gradlew verifyPlugin     # API compatibility check (catches binary-incompatible calls)
./gradlew test             # JUnit 5 unit tests (no IDE runtime needed)
```

## Notes for Claude
- **Do not add `@Suppress("UnstableApiUsage")`** unless specifically needed; prefer
  using stable API overloads first.
- `SqlScopeMenuGroup` extends `ActionGroup` (not `DefaultActionGroup`) and owns all
  menu building in `getChildren()` — do not re-add child groups via plugin.xml.
- When updating actions, always implement `getActionUpdateThread()` returning `BGT`
  unless the update() body requires EDT-bound model access.
- The `bundledPlugin("com.intellij.database")` dependency resolves
  `com.intellij.sql.dialects.SqlDialectMappings` (in the sql package within the db plugin).
- Use `/architecture` for file map, action hierarchy, and dependency details.
- Use `/api-reference` for IntelliJ SDK API details, threading rules, and verified API facts.
- Use `/inspect-api` for Python scripts that search IntelliJ SDK JARs.

## Compact instructions
When compacting, preserve: current task context, code changes made, API findings,
and error states. Drop: verbose tool output, intermediate search results, file contents
that have been summarized.
