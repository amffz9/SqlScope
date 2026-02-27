#!/usr/bin/env python3
"""Search for classes by partial name or by method name.

Usage:
    find_class.py DbObject              # classes matching "DbObject"
    find_class.py -m isSystem           # classes defining a method named "isSystem"
    find_class.py -f displayName        # classes defining a field named "displayName"
    find_class.py --reindex TreePattern # rebuild index, then search
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from class_index import ensure_index, search_classes, search_methods, search_fields


def main():
    parser = argparse.ArgumentParser(description="Search for classes by name or method")
    parser.add_argument("pattern", nargs="?", help="Partial class name to search for")
    parser.add_argument("-m", "--method", help="Search for classes defining this method")
    parser.add_argument("-f", "--field", help="Search for classes defining this field")
    parser.add_argument("--reindex", action="store_true", help="Force rebuild the index")
    parser.add_argument("--inner", action="store_true", help="Include inner classes")
    parser.add_argument("--scope", default="all", choices=["db", "all"], help="JAR scope (default: all)")
    args = parser.parse_args()

    if not args.pattern and not args.method and not args.field:
        parser.error("Provide a class name pattern, -m <method>, or -f <field>")

    conn = ensure_index(scope=args.scope, force=args.reindex)

    if args.method:
        results = search_methods(conn, args.method, scope=args.scope)
        if not results:
            print(f"No classes found with method matching '{args.method}'.")
            conn.close()
            return

        # Group by class
        by_class = {}
        for fqcn, jar_name, sig in results:
            by_class.setdefault((fqcn, jar_name), []).append(sig)

        print(f"Found {len(by_class)} classes with method matching '{args.method}':")
        print("---")
        for (fqcn, jar_name), sigs in by_class.items():
            print(f"=== {fqcn} ({jar_name}) ===")
            for sig in sigs:
                print(f"  {sig}")
            print()

    elif args.field:
        results = search_fields(conn, args.field)
        if not results:
            print(f"No classes found with field matching '{args.field}'.")
            conn.close()
            return

        by_class = {}
        for fqcn, jar_name, type_name, fname in results:
            by_class.setdefault((fqcn, jar_name), []).append(f"{type_name} {fname}")

        print(f"Found {len(by_class)} classes with field matching '{args.field}':")
        print("---")
        for (fqcn, jar_name), fields in by_class.items():
            print(f"=== {fqcn} ({jar_name}) ===")
            for f in fields:
                print(f"  {f}")
            print()

    else:
        results = search_classes(conn, args.pattern, include_inner=args.inner)
        if not results:
            print(f"No classes matching '{args.pattern}'.")
            conn.close()
            return
        print(f"Found {len(results)} classes matching '{args.pattern}':")
        print("---")
        current_jar = None
        for fqcn, jar_name in results:
            if jar_name != current_jar:
                if current_jar is not None:
                    print()
                print(f"{jar_name}:")
                current_jar = jar_name
            print(f"  {fqcn}")

    conn.close()


if __name__ == "__main__":
    main()
