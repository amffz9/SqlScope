# SQLScope

An IntelliJ/PhpStorm plugin that lets you assign SQL dialects and data source resolution scopes to files and directories from a right-click context menu — no more digging through Settings → Languages & Frameworks → SQL Dialects.

## The Problem

When working on projects that mix SQL across multiple directories (e.g. `src/migrations/` using MySQL and `src/reporting/` using PostgreSQL), setting the correct dialect and resolution scope for each file or directory requires several clicks through the IDE settings panel. SQLScope puts those mappings directly in the Project View context menu.

## Features

- **Set SQL Dialect** — right-click any file or directory and assign MySQL, PostgreSQL, SQLite, MariaDB, Oracle SQL*Plus, SQL Server (T-SQL), or Generic SQL
- **Smart dialect ordering** — dialects that match your configured datasources appear at the top; the rest are tucked into a "More Dialects" submenu
- **Set Resolution Scope** — associate a file or directory with a specific datasource or schema for accurate SQL symbol resolution and autocomplete
- **Multi-selection** — select multiple files/directories and apply mappings to all at once
- **Clear mappings** — remove a dialect or scope assignment in one click
- **Persistent** — mappings are saved to `.idea/sqlDialects.xml` and committed to VCS alongside your project

## Menu Structure

```
Right-click a file or directory in Project View
└── SQLScope
    ├── ── Dialect ────────────────────
    ├── MySQL              ← matches your configured datasources
    ├── PostgreSQL         ← matches your configured datasources
    ├── More Dialects ▶
    │   ├── Generic SQL
    │   ├── MariaDB
    │   ├── Oracle SQL*Plus
    │   ├── SQLite
    │   └── SQL Server (T-SQL)
    ├── Clear Dialect
    ├── ── Resolution Scope ───────────
    ├── information_schema
    ├── my_app_db
    ├── MySQL @ localhost
    └── Clear Resolution Scope
```

When no datasources are configured, all dialects appear flat and the Resolution Scope section is hidden.

## Requirements

- PhpStorm, IntelliJ IDEA Ultimate, or DataGrip (requires the bundled Database Tools & SQL plugin)
- IDE build 2025.3 or later

## Building from Source

```bash
./gradlew buildPlugin      # → build/distributions/SQLScope-<version>.zip
./gradlew runIde           # launch a sandboxed IDE for live testing
./gradlew verifyPlugin     # API compatibility check
./gradlew test             # unit tests (no IDE runtime required)
```

Requires JDK 21+. The build targets PhpStorm 2025.3.

## License

MIT
