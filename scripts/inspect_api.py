#!/usr/bin/env python3
"""Show a class's full API (methods and fields).

By default, queries the SQLite index (instant). Use --javap for raw javap output.

Usage:
    inspect_api.py TreePatternUtils
    inspect_api.py com.intellij.database.util.TreePattern
    inspect_api.py --javap com.intellij.database.psi.DbElement
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from class_index import (
    ensure_index, resolve_class, run_javap,
    get_class_methods, get_class_fields, get_class_info,
    get_class_interfaces, format_access_flags
)


def main():
    parser = argparse.ArgumentParser(description="Show class API")
    parser.add_argument("classname", help="Class name (simple or fully qualified)")
    parser.add_argument("--javap", action="store_true", help="Use raw javap output instead of index")
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
        print(run_javap(jar_path, fqcn))
    else:
        # Show class info from index
        info = get_class_info(conn, fqcn)
        if info:
            superclass, access_flags = info
            modifiers = format_access_flags(access_flags)
            ifaces = get_class_interfaces(conn, fqcn)

            # Build class declaration
            decl_parts = [modifiers]
            if access_flags & 0x0200:  # ACC_INTERFACE
                decl_parts.append("interface")
            elif access_flags & 0x0400:  # ACC_ABSTRACT
                decl_parts.append("abstract class")
            else:
                decl_parts.append("class")
            decl_parts.append(fqcn)

            if superclass and superclass != "java.lang.Object":
                decl_parts.append(f"extends {superclass}")
            if ifaces:
                keyword = "extends" if (access_flags & 0x0200) else "implements"
                decl_parts.append(f"{keyword} {', '.join(ifaces)}")

            print(' '.join(decl_parts))
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

        if not fields and not methods:
            print("(no public/protected members found in index)")
            print("Use --javap for raw javap output including private members.")

    conn.close()


if __name__ == "__main__":
    main()
