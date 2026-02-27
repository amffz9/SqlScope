---
name: api-reference
description: IntelliJ SDK API reference for SQLScope — key APIs, threading rules, known patterns, and verified API facts. Use when working with dialect, resolution scope, or datasource APIs.
user-invocable: true
---

## Key APIs

| Feature | API | Persistence |
|---|---|---|
| SQL Dialect | `SqlDialectMappings.getInstance(project).setMapping(file, language)` | `.idea/sqlDialects.xml` |
| Data source list | `DbPsiFacade.getInstance(project).dataSources` | — (read-only here) |
| DBMS of a datasource | `DasDataSource.getDbms(): Dbms` (`com.intellij.database.Dbms`) | — |
| DBMS display name | `Dbms.displayName` — e.g. "MySQL", "Microsoft SQL Server" | — |
| Resolution scope | `SqlResolveMappings.getInstance(project).setMapping(file, pattern)` where `pattern = TreePattern(TreePatternUtils.create(scope))` | `.idea/sqldialects.xml` |

## Threading Rules
- All `update()` methods use `ActionUpdateThread.BGT` (background thread) — safe because
  they only read from `AnActionEvent.getData()`.
- `ActionGroup.getChildren()` runs on EDT; keep it fast (no I/O, no network).

## Known Limitations / TODOs

### Resolution Scope API — IMPLEMENTED
`SqlScopeService.setResolutionScope()` and `clearResolutionScope()` are fully implemented
using `SqlResolveMappings.getInstance(project).setMapping(directory, pattern)` where
`pattern` is built with `TreePattern(TreePatternUtils.create(scope))`.

- `scope` can be a `DbDataSource` (whole server) or a `DasNamespace` (individual schema/database).
- Persists in `.idea/sqldialects.xml`, mirroring Settings → Languages & Frameworks → SQL Resolution Scopes.

### Dialect Language IDs — RESOLVED
`DialectRegistry` now uses dynamic discovery via `SqlLanguageDialect.getRegisteredLanguages()`,
so hardcoded IDs are no longer needed.

### Stretch Goals (v1.1)
- Add a tree decorator to badge directories that have a dialect assigned.

## Verified API Facts (from bytecode inspection)
- `TreePatternUtils.create(DasObject)` returns `TreePatternNode.Group` (NOT `TreePattern`)
- `TreePattern` has a constructor: `TreePattern(TreePatternNode.Group)` — use this to wrap
- Correct usage: `val pattern = TreePattern(TreePatternUtils.create(scope))`
- WRONG: `TreePatternUtils.create(scope) as TreePattern` — throws ClassCastException
- `Dbms` package: `com.intellij.database.Dbms` (NOT `.model.Dbms`)
- `DasDataSource.getDbms()` → `Dbms` (Kotlin: `.dbms`)
