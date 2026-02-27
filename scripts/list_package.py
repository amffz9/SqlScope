#!/usr/bin/env python3
"""List all classes in a given package.

Usage:
    list_package.py com.intellij.database.psi
    list_package.py com.intellij.database.util
    list_package.py com.intellij.sql.dialects
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from class_index import ensure_index, list_package


def main():
    parser = argparse.ArgumentParser(description="List classes in a package")
    parser.add_argument("package", help="Fully qualified package name")
    parser.add_argument("--reindex", action="store_true", help="Force rebuild the index")
    parser.add_argument("--inner", action="store_true", help="Include inner classes")
    parser.add_argument("--scope", default="all", choices=["db", "all"], help="JAR scope (default: all)")
    args = parser.parse_args()

    conn = ensure_index(scope=args.scope, force=args.reindex)
    results = list_package(conn, args.package, include_inner=args.inner)

    if not results:
        print(f"No classes found in package '{args.package}'.")
        conn.close()
        sys.exit(1)

    print(f"Package: {args.package}")
    print(f"{len(results)} classes")
    print("---")

    current_jar = None
    for simple, fqcn, jar_name in results:
        if jar_name != current_jar:
            if current_jar is not None:
                print()
            print(f"{jar_name}:")
            current_jar = jar_name
        print(f"  {simple}")

    conn.close()


if __name__ == "__main__":
    main()
