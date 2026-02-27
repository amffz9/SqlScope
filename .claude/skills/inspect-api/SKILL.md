---
name: inspect-api
description: Python tools for inspecting IntelliJ SDK JARs — find classes, methods, fields, hierarchy. Use when you need to look up IntelliJ Platform or Database Tools APIs.
user-invocable: true
---

## API Inspection Scripts (scripts/)

Python tools backed by a persistent SQLite index (~316k classes, ~1s lookups).
Index lives at `~/.cache/intellij-class-index/index.db`, auto-rebuilds when JARs change.
Use `--reindex` to force rebuild. Use `--scope db` to limit to DatabaseTools JARs only.

### Commands

```bash
# Find classes by partial name
./scripts/find_class.py <partial>
./scripts/find_class.py TreePattern

# Find classes defining a method (instant, SQL-backed)
./scripts/find_class.py -m <method>
./scripts/find_class.py -m isSystem

# Find classes defining a field
./scripts/find_class.py -f <field>
./scripts/find_class.py -f displayName

# Show class methods/fields from index
./scripts/inspect_api.py <ClassName>
./scripts/inspect_api.py --javap <ClassName>   # raw javap fallback

# Show superclass, interfaces, inner classes
./scripts/inspect_hierarchy.py <ClassName>

# List all classes in a package
./scripts/list_package.py <package>
./scripts/list_package.py com.intellij.database.psi
```

All accept simple names (`TreePattern`) or FQCNs (`com.intellij.database.util.TreePattern`).

### Architecture
`bytecode.py` (class file parser) → `class_index.py` (indexer + queries) → CLI scripts.

### Flags
- `--reindex` — force rebuild the SQLite index
- `--scope db` — limit to DatabaseTools JARs only (faster, fewer results)
- `--scope all` — all IDE JARs (default)
- `--javap` — use raw javap output instead of index (inspect_api/inspect_hierarchy)
- `--inner` — include inner classes in find_class results
