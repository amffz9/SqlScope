#!/usr/bin/env python3
"""Shared module for IntelliJ class inspection tools.

Handles JAR discovery, persistent SQLite indexing with bytecode parsing,
class/method/field lookup, and javap execution.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional

from bytecode import parse_class


# ── Configuration ───────────────────────────────────────────────────────────

CACHE_DIR = Path.home() / ".cache" / "intellij-class-index"
DB_PATH = CACHE_DIR / "index.db"

GRADLE_CACHE = Path(os.environ.get("INSPECT_SEARCH_ROOT", Path.home() / ".gradle" / "caches"))
PLUGIN_NAME = os.environ.get("INSPECT_PLUGIN", "DatabaseTools")
IDE_NAME = os.environ.get("INSPECT_IDE", "PhpStorm")

SCHEMA_VERSION = 2  # Bump when schema changes to force rebuild


# ── JAR Discovery ──────────────────────────────────────────────────────────

def _find_plugin_dir() -> Optional[Path]:
    """Find the IDE plugin directory in the Gradle cache."""
    for pattern in [f"*{IDE_NAME}-2025.3*", f"*{IDE_NAME}*"]:
        for d in GRADLE_CACHE.rglob(pattern):
            candidate = d / "plugins" / PLUGIN_NAME if d.is_dir() else None
            if candidate and candidate.is_dir():
                return candidate
            if d.is_dir() and d.name == PLUGIN_NAME:
                return d
    for d in GRADLE_CACHE.rglob(PLUGIN_NAME):
        if d.is_dir() and "plugins" in str(d):
            return d
    return None


def discover_jars(scope: str = "all") -> list[Path]:
    """Discover JARs to index.

    scope="db"  → only plugin JARs
    scope="all" → plugin + platform + other plugins
    """
    jars = []
    plugin_dir = _find_plugin_dir()

    if plugin_dir:
        for jar in plugin_dir.rglob("*.jar"):
            jars.append(jar)

        if scope == "all":
            ide_root = plugin_dir.parent.parent
            lib_dir = ide_root / "lib"
            if lib_dir.is_dir():
                for jar in lib_dir.rglob("*.jar"):
                    jars.append(jar)
            plugins_dir = ide_root / "plugins"
            if plugins_dir.is_dir():
                for jar in plugins_dir.rglob("*.jar"):
                    if PLUGIN_NAME not in str(jar):
                        jars.append(jar)

    if not jars:
        print(f"No {IDE_NAME}/{PLUGIN_NAME} found, scanning full Gradle cache...", file=sys.stderr)
        for jar in GRADLE_CACHE.rglob("*.jar"):
            jars.append(jar)

    # Deduplicate by filename, keeping first occurrence
    seen = set()
    unique = []
    for jar in jars:
        if jar.name not in seen:
            seen.add(jar.name)
            unique.append(jar)
    return unique


# ── SQLite Schema ──────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jars (
    id INTEGER PRIMARY KEY,
    jar_path TEXT UNIQUE NOT NULL,
    jar_name TEXT NOT NULL,
    mtime REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY,
    jar_id INTEGER NOT NULL REFERENCES jars(id) ON DELETE CASCADE,
    fqcn TEXT NOT NULL,
    package TEXT NOT NULL,
    simple_name TEXT NOT NULL,
    is_inner INTEGER NOT NULL,
    superclass TEXT,
    access_flags INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS interfaces (
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    interface_fqcn TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS methods (
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    descriptor TEXT NOT NULL,
    signature TEXT NOT NULL,
    access_flags INTEGER NOT NULL,
    is_static INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fields (
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    descriptor TEXT NOT NULL,
    type_name TEXT NOT NULL,
    access_flags INTEGER NOT NULL,
    is_static INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_classes_fqcn ON classes(fqcn);
CREATE INDEX IF NOT EXISTS idx_classes_simple ON classes(simple_name);
CREATE INDEX IF NOT EXISTS idx_classes_package ON classes(package);
CREATE INDEX IF NOT EXISTS idx_methods_name ON methods(name);
CREATE INDEX IF NOT EXISTS idx_fields_name ON fields(name);
CREATE INDEX IF NOT EXISTS idx_interfaces_fqcn ON interfaces(interface_fqcn);
CREATE INDEX IF NOT EXISTS idx_classes_jar ON classes(jar_id);
"""


def _get_db() -> sqlite3.Connection:
    """Open (or create) the SQLite index database."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Check schema version — if outdated, drop everything and rebuild
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        current_version = int(row[0]) if row else 0
    except sqlite3.OperationalError:
        current_version = 0

    if current_version != SCHEMA_VERSION:
        # Drop all tables and recreate
        for table in ['methods', 'fields', 'interfaces', 'classes', 'jars', 'meta']:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.executescript(_SCHEMA_SQL)
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)",
                      (str(SCHEMA_VERSION),))
        conn.commit()
    else:
        # Ensure tables exist (first run after schema version match)
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

    return conn


# ── Indexing ───────────────────────────────────────────────────────────────

def _index_jar(conn: sqlite3.Connection, jar_path: Path, jar_id: int) -> int:
    """Parse all .class files in a JAR and insert into the database.
    Returns the number of classes indexed.
    """
    class_count = 0
    class_batch = []
    iface_batch = []
    method_batch = []
    field_batch = []

    try:
        with zipfile.ZipFile(jar_path, "r") as zf:
            for entry in zf.namelist():
                if not entry.endswith(".class"):
                    continue

                fqcn = entry[:-6].replace("/", ".")
                is_inner = "$" in fqcn
                dot_idx = fqcn.rfind(".")
                package = fqcn[:dot_idx] if dot_idx >= 0 else ""
                simple = fqcn[dot_idx + 1:] if dot_idx >= 0 else fqcn

                # Parse bytecode
                try:
                    raw = zf.read(entry)
                    info = parse_class(raw)
                except Exception:
                    info = None

                superclass = info.super_class if info else None
                access_flags = info.access_flags if info else 0

                # Use a placeholder class_id — we'll get it after insert
                class_batch.append((
                    jar_id, fqcn, package, simple, int(is_inner),
                    superclass, access_flags
                ))

                if info:
                    # Store interface/method/field data keyed by fqcn
                    # We'll resolve class_ids after bulk insert
                    for iface_fqcn in info.interfaces:
                        iface_batch.append((fqcn, iface_fqcn))
                    for name, desc, sig, flags, is_static in info.methods:
                        method_batch.append((fqcn, name, desc, sig, flags, int(is_static)))
                    for name, desc, type_name, flags, is_static in info.fields:
                        field_batch.append((fqcn, name, desc, type_name, flags, int(is_static)))

                class_count += 1

    except (zipfile.BadZipFile, OSError):
        return 0

    if not class_batch:
        return 0

    # Bulk insert classes
    conn.executemany(
        "INSERT INTO classes (jar_id, fqcn, package, simple_name, is_inner, superclass, access_flags) "
        "VALUES (?,?,?,?,?,?,?)",
        class_batch
    )

    if iface_batch or method_batch or field_batch:
        # Build fqcn → class_id map for this JAR
        fqcn_to_id = {}
        for row in conn.execute(
            "SELECT id, fqcn FROM classes WHERE jar_id = ?", (jar_id,)
        ):
            fqcn_to_id[row[1]] = row[0]

        # Insert interfaces
        if iface_batch:
            conn.executemany(
                "INSERT INTO interfaces (class_id, interface_fqcn) VALUES (?,?)",
                [(fqcn_to_id[fqcn], iface) for fqcn, iface in iface_batch
                 if fqcn in fqcn_to_id]
            )

        # Insert methods
        if method_batch:
            conn.executemany(
                "INSERT INTO methods (class_id, name, descriptor, signature, access_flags, is_static) "
                "VALUES (?,?,?,?,?,?)",
                [(fqcn_to_id[fqcn], name, desc, sig, flags, is_static)
                 for fqcn, name, desc, sig, flags, is_static in method_batch
                 if fqcn in fqcn_to_id]
            )

        # Insert fields
        if field_batch:
            conn.executemany(
                "INSERT INTO fields (class_id, name, descriptor, type_name, access_flags, is_static) "
                "VALUES (?,?,?,?,?,?)",
                [(fqcn_to_id[fqcn], name, desc, type_name, flags, is_static)
                 for fqcn, name, desc, type_name, flags, is_static in field_batch
                 if fqcn in fqcn_to_id]
            )

    return class_count


def build_index(conn: sqlite3.Connection, scope: str = "all", force: bool = False) -> int:
    """Build or incrementally update the class index. Returns total class count."""
    jars_on_disk = discover_jars(scope)
    if not jars_on_disk:
        print("No JARs found. Check INSPECT_SEARCH_ROOT.", file=sys.stderr)
        return 0

    if force:
        # Full rebuild
        conn.execute("DELETE FROM jars")  # CASCADE deletes classes, methods, etc.
        conn.commit()

    # Check scope — if upgrading from "db" to "all", force rebuild
    row = conn.execute("SELECT value FROM meta WHERE key='scope'").fetchone()
    current_scope = row[0] if row else None
    if current_scope == "db" and scope == "all":
        conn.execute("DELETE FROM jars")
        conn.commit()

    # Build map of existing indexed JARs
    existing = {}  # jar_path → (id, mtime)
    for jar_id, jar_path, mtime in conn.execute("SELECT id, jar_path, mtime FROM jars"):
        existing[jar_path] = (jar_id, mtime)

    # Determine what needs updating
    disk_paths = {str(j): j for j in jars_on_disk}
    to_add = []      # (path_str, Path)
    to_update = []   # (path_str, Path, old_jar_id)
    unchanged = 0

    for path_str, path in disk_paths.items():
        if path_str not in existing:
            to_add.append((path_str, path))
        else:
            old_id, old_mtime = existing[path_str]
            try:
                current_mtime = path.stat().st_mtime
            except OSError:
                continue
            if abs(current_mtime - old_mtime) > 0.001:
                to_update.append((path_str, path, old_id))
            else:
                unchanged += 1

    # Remove JARs no longer on disk
    removed_paths = set(existing.keys()) - set(disk_paths.keys())
    if removed_paths:
        for rp in removed_paths:
            jar_id = existing[rp][0]
            conn.execute("DELETE FROM jars WHERE id = ?", (jar_id,))

    total_work = len(to_add) + len(to_update)
    if total_work == 0 and not removed_paths:
        count = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        if count > 0:
            return count

    if total_work > 0:
        print(f"Indexing {total_work} JARs ({unchanged} unchanged, {len(removed_paths)} removed)...",
              file=sys.stderr)

    total_classes = 0
    processed = 0
    start_time = time.time()

    # Process new JARs
    for path_str, path in to_add:
        processed += 1
        if processed % 20 == 0 or processed == total_work:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_work - processed) / rate if rate > 0 else 0
            print(f"  {processed}/{total_work} JARs ({rate:.0f}/s, ~{eta:.0f}s remaining)...",
                  file=sys.stderr, end="\r")

        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        conn.execute("INSERT INTO jars (jar_path, jar_name, mtime) VALUES (?,?,?)",
                      (path_str, path.name, mtime))
        jar_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        total_classes += _index_jar(conn, path, jar_id)

    # Process updated JARs
    for path_str, path, old_id in to_update:
        processed += 1
        if processed % 20 == 0 or processed == total_work:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_work - processed) / rate if rate > 0 else 0
            print(f"  {processed}/{total_work} JARs ({rate:.0f}/s, ~{eta:.0f}s remaining)...",
                  file=sys.stderr, end="\r")

        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        # Delete old data (CASCADE handles classes/methods/etc.)
        conn.execute("DELETE FROM jars WHERE id = ?", (old_id,))
        conn.execute("INSERT INTO jars (jar_path, jar_name, mtime) VALUES (?,?,?)",
                      (path_str, path.name, mtime))
        jar_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        total_classes += _index_jar(conn, path, jar_id)

    conn.execute("INSERT OR REPLACE INTO meta VALUES ('scope', ?)", (scope,))
    conn.commit()

    total_count = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    if total_work > 0:
        elapsed = time.time() - start_time
        print(f"\nIndexed {total_classes} new classes in {elapsed:.1f}s. "
              f"Total: {total_count} classes from {len(jars_on_disk)} JARs.",
              file=sys.stderr)

    return total_count


def ensure_index(scope: str = "all", force: bool = False) -> sqlite3.Connection:
    """Get a connection with an up-to-date index."""
    conn = _get_db()
    build_index(conn, scope, force)
    return conn


# ── Query Helpers ──────────────────────────────────────────────────────────

def search_classes(conn: sqlite3.Connection, partial: str, include_inner: bool = False) -> list[tuple]:
    """Search for classes by partial name. Returns (fqcn, jar_name) tuples."""
    query = """
        SELECT DISTINCT c.fqcn, j.jar_name FROM classes c
        JOIN jars j ON c.jar_id = j.id
        WHERE (c.simple_name LIKE ? OR c.fqcn LIKE ?)
    """
    if not include_inner:
        query += " AND c.is_inner = 0"
    query += " ORDER BY c.fqcn"
    pattern = f"%{partial}%"
    return conn.execute(query, (pattern, pattern)).fetchall()


def find_class_exact(conn: sqlite3.Connection, name: str) -> list[tuple]:
    """Find a class by exact FQCN or simple name. Returns (fqcn, jar_path, jar_name) tuples."""
    rows = conn.execute(
        "SELECT DISTINCT c.fqcn, j.jar_path, j.jar_name FROM classes c "
        "JOIN jars j ON c.jar_id = j.id WHERE c.fqcn = ? AND c.is_inner = 0",
        (name,)
    ).fetchall()
    if rows:
        return rows
    rows = conn.execute(
        "SELECT DISTINCT c.fqcn, j.jar_path, j.jar_name FROM classes c "
        "JOIN jars j ON c.jar_id = j.id WHERE c.simple_name = ? AND c.is_inner = 0",
        (name,)
    ).fetchall()
    return rows


def list_package(conn: sqlite3.Connection, package: str, include_inner: bool = False) -> list[tuple]:
    """List all classes in a package. Returns (simple_name, fqcn, jar_name) tuples."""
    query = """
        SELECT DISTINCT c.simple_name, c.fqcn, j.jar_name FROM classes c
        JOIN jars j ON c.jar_id = j.id
        WHERE c.package = ?
    """
    if not include_inner:
        query += " AND c.is_inner = 0"
    query += " ORDER BY c.simple_name"
    return conn.execute(query, (package,)).fetchall()


def suggest_similar(conn: sqlite3.Connection, name: str, limit: int = 5) -> list[str]:
    """Suggest similar class names for fuzzy matching."""
    rows = conn.execute(
        "SELECT DISTINCT fqcn FROM classes WHERE simple_name LIKE ? AND is_inner = 0 ORDER BY fqcn LIMIT ?",
        (f"%{name}%", limit)
    ).fetchall()
    return [r[0] for r in rows]


def get_inner_classes(conn: sqlite3.Connection, fqcn: str) -> list[str]:
    """Get inner classes for a given FQCN from the index."""
    prefix = fqcn + "$"
    rows = conn.execute(
        "SELECT DISTINCT fqcn FROM classes WHERE fqcn LIKE ? ORDER BY fqcn",
        (prefix + "%",)
    ).fetchall()
    return [r[0] for r in rows]


# ── Method/Field Queries (new — no javap needed) ──────────────────────────

def search_methods(conn: sqlite3.Connection, method_name: str, scope: str = "db") -> list[tuple]:
    """Search for classes defining a method by name.
    Returns (fqcn, jar_name, signature) tuples.
    """
    query = """
        SELECT DISTINCT c.fqcn, j.jar_name, m.signature
        FROM methods m
        JOIN classes c ON m.class_id = c.id
        JOIN jars j ON c.jar_id = j.id
        WHERE m.name LIKE ?
        AND c.is_inner = 0
        ORDER BY c.fqcn, m.signature
    """
    return conn.execute(query, (f"%{method_name}%",)).fetchall()


def search_fields(conn: sqlite3.Connection, field_name: str) -> list[tuple]:
    """Search for classes defining a field by name.
    Returns (fqcn, jar_name, type_name, field_name) tuples.
    """
    query = """
        SELECT DISTINCT c.fqcn, j.jar_name, f.type_name, f.name
        FROM fields f
        JOIN classes c ON f.class_id = c.id
        JOIN jars j ON c.jar_id = j.id
        WHERE f.name LIKE ?
        AND c.is_inner = 0
        ORDER BY c.fqcn
    """
    return conn.execute(query, (f"%{field_name}%",)).fetchall()


def get_class_methods(conn: sqlite3.Connection, fqcn: str) -> list[tuple]:
    """Get all methods for a class. Returns (signature, is_static, access_flags) tuples."""
    return conn.execute("""
        SELECT m.signature, m.is_static, m.access_flags
        FROM methods m
        JOIN classes c ON m.class_id = c.id
        WHERE c.fqcn = ?
        ORDER BY m.name
    """, (fqcn,)).fetchall()


def get_class_fields(conn: sqlite3.Connection, fqcn: str) -> list[tuple]:
    """Get all fields for a class. Returns (name, type_name, is_static, access_flags) tuples."""
    return conn.execute("""
        SELECT f.name, f.type_name, f.is_static, f.access_flags
        FROM fields f
        JOIN classes c ON f.class_id = c.id
        WHERE c.fqcn = ?
        ORDER BY f.name
    """, (fqcn,)).fetchall()


def get_class_info(conn: sqlite3.Connection, fqcn: str) -> Optional[tuple]:
    """Get class metadata. Returns (superclass, access_flags) or None."""
    row = conn.execute(
        "SELECT superclass, access_flags FROM classes WHERE fqcn = ? LIMIT 1",
        (fqcn,)
    ).fetchone()
    return row


def get_class_interfaces(conn: sqlite3.Connection, fqcn: str) -> list[str]:
    """Get interfaces implemented by a class."""
    rows = conn.execute("""
        SELECT i.interface_fqcn
        FROM interfaces i
        JOIN classes c ON i.class_id = c.id
        WHERE c.fqcn = ?
        ORDER BY i.interface_fqcn
    """, (fqcn,)).fetchall()
    return [r[0] for r in rows]


# ── javap Execution (still available for raw output) ──────────────────────

def _check_javap():
    if not shutil.which("javap"):
        print("Error: javap not found on PATH. Install a JDK.", file=sys.stderr)
        sys.exit(1)


def run_javap(jar_path: str, fqcn: str, flags: str = "-p") -> str:
    """Run javap on a class and return its output."""
    _check_javap()
    try:
        result = subprocess.run(
            ["javap", flags, "-classpath", jar_path, fqcn],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"javap timed out for {fqcn}"


def resolve_class(conn: sqlite3.Connection, name: str) -> Optional[tuple]:
    """Resolve a class name to (fqcn, jar_path). Handles simple and qualified names.
    Returns None if not found (prints suggestions).
    """
    rows = find_class_exact(conn, name)
    if not rows:
        suggestions = suggest_similar(conn, name.split(".")[-1])
        print(f"Class not found: {name}", file=sys.stderr)
        if suggestions:
            print("Did you mean:", file=sys.stderr)
            for s in suggestions:
                print(f"  {s}", file=sys.stderr)
        return None

    if len(rows) > 1:
        print(f"Found {len(rows)} matches — using first:", file=sys.stderr)
        for fqcn, jar_path, jar_name in rows:
            print(f"  {fqcn} ({jar_name})", file=sys.stderr)

    fqcn, jar_path, jar_name = rows[0]
    return (fqcn, jar_path)


# ── Access Flag Formatting ────────────────────────────────────────────────

def format_access_flags(flags: int, is_method: bool = False) -> str:
    """Convert access flags to human-readable modifiers string."""
    parts = []
    if flags & 0x0001: parts.append('public')
    if flags & 0x0002: parts.append('private')
    if flags & 0x0004: parts.append('protected')
    if flags & 0x0008: parts.append('static')
    if flags & 0x0010: parts.append('final')
    if is_method and (flags & 0x0020): parts.append('synchronized')
    if flags & 0x0100: parts.append('native')
    if flags & 0x0400: parts.append('abstract')
    return ' '.join(parts)
