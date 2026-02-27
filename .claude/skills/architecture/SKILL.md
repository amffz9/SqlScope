---
name: architecture
description: SQLScope plugin architecture — file map, action hierarchy, menu structure, and dependency notes. Use when working on plugin structure or adding new actions.
user-invocable: true
---

## File Map

```
src/main/kotlin/com/sqlscope/
├── actions/
│   ├── SqlScopeMenuGroup.kt   Top-level group + dynamic flat menu builder
│   ├── SetDialectAction.kt    Applies one dialect via SqlDialectMappings
│   ├── ClearDialectAction.kt  Clears dialect (setMapping null)
│   ├── SetResolutionAction.kt Associates file/dir with a DbDataSource or schema
│   └── ClearResolutionAction.kt  Clears resolution scope
├── services/
│   └── SqlScopeService.kt     Core service; owns all mapping + notification logic
└── util/
    └── DialectRegistry.kt     Discovers SQL dialects from the Language registry

src/main/resources/META-INF/plugin.xml   Plugin descriptor (actions, service, notifications)
src/test/kotlin/com/sqlscope/
└── DialectRegistryTest.kt           Pure unit tests (no IDE runtime required)
```

## Action Hierarchy (Project View popup)

```
ProjectViewPopupMenu
└── SQLScope  (SqlScopeMenuGroup — hidden unless a file or directory is selected)
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

## Dependency Notes
- `com.intellij.modules.platform` — always present; provides core platform APIs.
- `com.intellij.database` — Database Tools & SQL plugin.
  Bundled in PhpStorm, IntelliJ IDEA Ultimate, DataGrip.
  **NOT** bundled in IntelliJ IDEA Community or Android Studio.
- If targeting Community edition is needed, wrap all database API calls in
  `@OptionalDependency` and add `<depends optional="true">com.intellij.database</depends>`
  to plugin.xml.
