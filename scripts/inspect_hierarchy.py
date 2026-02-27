#!/usr/bin/env python3
"""Show a class's hierarchy: superclass, interfaces, methods, fields, and inner classes.

All data comes from the SQLite index (instant). Use --javap for raw javap output.

Usage:
    inspect_hierarchy.py com.intellij.database.psi.DbElement
    inspect_hierarchy.py TreePattern
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from class_index import (
    ensure_index, resolve_class, run_javap,
    get_class_info, get_class_interfaces, get_class_methods,
    get_class_fields, get_inner_classes, format_access_flags
)


def main():
    parser = argparse.ArgumentParser(description="Show class hierarchy and inner classes")
    parser.add_argument("classname", help="Class name (simple or fully qualified)")
    parser.add_argument("--javap", action="store_true", help="Use raw javap for declaration instead of index")
    parser.add_argument("--reindex", action="store_true", help="Force rebuild the index")
    parser.add_argument("--scope", default="all", choices=["db", "all"], help="JAR scope (default: all)")
    args = parser.parse_args()

    conn = ensure_index(scope=args.scope, force=args.reindex)
    resolved = resolve_class(conn, args.classname)
    if not resolved:
        sys.exit(1)

    fqcn, jar_path = resolved
    print(f"=== {fqcn} ===")
    print(f"jar: {Path(jar_path).name}")
    print()

    if args.javap:
        print("--- Declaration & Methods (javap) ---")
        print(run_javap(jar_path, fqcn))
    else:
        # Class info from index
        info = get_class_info(conn, fqcn)
        if info:
            superclass, access_flags = info
            modifiers = format_access_flags(access_flags)

            print("--- Class Declaration ---")
            if access_flags & 0x0200:
                kind = "interface"
            elif access_flags & 0x0400:
                kind = "abstract class"
            elif access_flags & 0x4000:
                kind = "enum"
            else:
                kind = "class"
            print(f"  {modifiers} {kind} {fqcn}")

            if superclass and superclass != "java.lang.Object":
                print(f"  extends {superclass}")

            ifaces = get_class_interfaces(conn, fqcn)
            if ifaces:
                keyword = "extends" if (access_flags & 0x0200) else "implements"
                print(f"  {keyword}:")
                for iface in ifaces:
                    print(f"    {iface}")
            print()

        # Fields
        fields = get_class_fields(conn, fqcn)
        if fields:
            print("--- Fields ---")
            for name, type_name, is_static, flags in fields:
                mods = format_access_flags(flags)
                static = "static " if is_static else ""
                print(f"  {mods} {static}{type_name} {name};")
            print()

        # Methods
        methods = get_class_methods(conn, fqcn)
        if methods:
            print("--- Methods ---")
            for sig, is_static, flags in methods:
                mods = format_access_flags(flags, is_method=True)
                static = "static " if is_static else ""
                print(f"  {mods} {static}{sig};")
            print()

    # Inner classes (always from index)
    inner = get_inner_classes(conn, fqcn)
    if inner:
        print("--- Inner Classes ---")
        for cls in inner:
            print(f"  {cls}")
        print()

    conn.close()


if __name__ == "__main__":
    main()
