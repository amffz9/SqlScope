# SQLScope — Claude Context

## What This Project Is
An IntelliJ/PhpStorm plugin (Kotlin) that adds a right-click context menu in the
Project View to quickly assign SQL dialects and data source resolution scopes to
directories, replacing the tedious Settings → Languages & Frameworks → SQL Dialects flow.

---

## Build & Run

```bash
./gradlew buildPlugin      # produces build/distributions/SQLScope-1.0.0.zip
./gradlew runIde           # launches a sandboxed PhpStorm/IntelliJ for live testing
./gradlew verifyPlugin     # API compatibility check (catches binary-incompatible calls)
./gradlew test             # JUnit 5 unit tests (no IDE runtime needed)
```

---

## Architecture

### File Map

```
src/main/kotlin/com/sqlscope/
├── actions/
│   ├── SqlScopeMenuGroup.kt   Top-level group + dynamic flat menu builder
│   ├── SetDialectAction.kt    Applies one dialect via SqlDialectMappings
│   ├── ClearDialectAction.kt  Clears dialect (setMapping null)
│   ├── SetResolutionAction.kt Associates directory with a DbDataSource or schema
│   └── ClearResolutionAction.kt  Clears resolution scope
├── services/
│   └── SqlScopeService.kt     Core service; owns all mapping + notification logic
└── util/
    └── DialectRegistry.kt     Discovers SQL dialects from the Language registry

src/main/resources/META-INF/plugin.xml   Plugin descriptor (actions, service, notifications)
src/test/kotlin/com/sqlscope/
└── DialectRegistryTest.kt           Pure unit tests (no IDE runtime required)
```

### Action Hierarchy (Project View popup)

```
ProjectViewPopupMenu
└── SQLScope  (SqlScopeMenuGroup — hidden unless a directory is selected)
    ├── ── Dialect ──────────────  Separator("Dialect")
    ├── MySQL                      dialect matching a configured datasource's DBMS
    ├── PostgreSQL                 dialect matching a configured datasource's DBMS
    ├── More Dialects ▶            DefaultActionGroup(popup=true) with remaining dialects
    │   ├── Generic SQL
    │   ├── MariaDB
    │   ├── Oracle SQL*Plus
    │   ├── SQLite
    │   └── SQL Server (T-SQL)
    ├── Clear Dialect
    ├── ── Resolution Scope ─────  Separator("Resolution Scope") — only if datasources exist
    ├── information_schema         schema scope (flat)
    ├── my_app_db                  schema scope (flat)
    ├── MySQL @ localhost          whole-server scope (flat)
    ├── PostgreSQL @ prod          whole-server scope (flat)
    └── Clear Resolution Scope
```

When no datasources are configured: all dialects appear flat (no "More Dialects" submenu)
and the Resolution Scope separator + items are omitted.

---

## Key APIs

| Feature | API | Persistence |
|---|---|---|
| SQL Dialect | `SqlDialectMappings.getInstance(project).setMapping(file, language)` | `.idea/sqlDialects.xml` |
| Data source list | `DbPsiFacade.getInstance(project).dataSources` | — (read-only here) |
| DBMS of a datasource | `DasDataSource.getDbms(): Dbms` (`com.intellij.database.Dbms`) | — |
| DBMS display name | `Dbms.displayName` — e.g. "MySQL", "Microsoft SQL Server" | — |
| Resolution scope | **NOT YET IMPLEMENTED** — see below | `.idea/sqlResolutionScopes.xml` (likely) |

### Threading Rules
- All `update()` methods use `ActionUpdateThread.BGT` (background thread) — safe because
  they only read from `AnActionEvent.getData()`.
- `ActionGroup.getChildren()` runs on EDT; keep it fast (no I/O, no network).

---

## Known Limitations / TODOs

### 1. Resolution Scope API (priority TODO)
`SqlScopeService.setResolutionScopeImpl()` currently throws `NotImplementedError`.
The SQL resolution scope API is not fully exposed as a stable public surface in all
IntelliJ Platform versions.

**How to find the correct API:**
1. Run `./gradlew runIde` and open any project.
2. Go to Settings → Languages & Frameworks → SQL Resolution Scopes and add a mapping.
3. Find the backing `Configurable` class in the IDE source:
   - Search for `SqlResolutionScopeConfigurable` or `SqlFileScopeManager`.
4. Candidate classes to try (check availability for your IDE build):
   - `com.intellij.sql.psi.SqlFileScopes.getInstance(project)`
   - `com.intellij.sql.dialects.SqlResolveScope`
   - `com.intellij.database.model.DasScopeMapping`
5. Implement the call in `setResolutionScopeImpl()` and `clearResolutionScopeImpl()`.

### 2. Dialect Language IDs
If a dialect shows "not available" at runtime, the Language ID registered by the IDE
may differ from the constant in `DialectRegistry`. Call `DialectRegistry.logRegisteredLanguages()`
from `actionPerformed` and check the IDE notification / log output.

Common IDs (verify against your IDE version):
- MySQL → `"MySQL"`
- PostgreSQL → `"PostgreSQL"`
- SQLite → `"SQLite"`
- MariaDB → `"MariaDB"`
- Oracle → `"OracleSqlPlus"`
- T-SQL → `"TSQL"`
- Generic SQL → `"GenericSQL"`

### 3. Stretch Goals (v1.1)
- Persist mappings in `.sqlscope.json` at the project root so they can be committed.
- On project open, read `.sqlscope.json` and call `SqlDialectMappings.setMapping()`.
- Add a tree decorator to badge directories that have a dialect assigned.

---

## Dependency Notes
- `com.intellij.modules.platform` — always present; provides core platform APIs.
- `com.intellij.database` — Database Tools & SQL plugin.
  Bundled in PhpStorm, IntelliJ IDEA Ultimate, DataGrip.
  **NOT** bundled in IntelliJ IDEA Community or Android Studio.
- If targeting Community edition is needed, wrap all database API calls in
  `@OptionalDependency` and add `<depends optional="true">com.intellij.database</depends>`
  to plugin.xml.

---

## Notes for Claude
- **Do not add `@Suppress("UnstableApiUsage")`** unless specifically needed; prefer
  using stable API overloads first.
- `SqlScopeMenuGroup` now extends `ActionGroup` (not `DefaultActionGroup`) and owns all
  menu building in `getChildren()` — do not re-add child groups via plugin.xml.
- When updating actions, always implement `getActionUpdateThread()` returning `BGT`
  unless the update() body requires EDT-bound model access.
- The `bundledPlugin("com.intellij.database")` dependency resolves
  `com.intellij.sql.dialects.SqlDialectMappings` (in the sql package within the db plugin).
