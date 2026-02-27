#!/usr/bin/env python3
"""JVM .class file bytecode parser.

Parses the constant pool, class header, interfaces, fields, and methods
from raw .class bytes. Uses only the standard library (struct + io).

Reference: https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html
"""

import struct
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────

# Constant pool tags
CP_UTF8 = 1
CP_INTEGER = 3
CP_FLOAT = 4
CP_LONG = 5
CP_DOUBLE = 6
CP_CLASS = 7
CP_STRING = 8
CP_FIELDREF = 9
CP_METHODREF = 10
CP_INTERFACE_METHODREF = 11
CP_NAME_AND_TYPE = 12
CP_METHOD_HANDLE = 15
CP_METHOD_TYPE = 16
CP_DYNAMIC = 17
CP_INVOKE_DYNAMIC = 18
CP_MODULE = 19
CP_PACKAGE = 20

# Access flags
ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_SYNCHRONIZED = 0x0020
ACC_BRIDGE = 0x0040
ACC_VARARGS = 0x0080
ACC_NATIVE = 0x0100
ACC_ABSTRACT = 0x0400
ACC_SYNTHETIC = 0x1000
ACC_ENUM = 0x4000


# ── Descriptor Decoding ───────────────────────────────────────────────────

def _decode_type(desc: str, pos: int) -> tuple[str, int]:
    """Decode one type from a JVM descriptor at position pos.
    Returns (human_readable, new_position).
    """
    ch = desc[pos]
    if ch == 'B':
        return 'byte', pos + 1
    elif ch == 'C':
        return 'char', pos + 1
    elif ch == 'D':
        return 'double', pos + 1
    elif ch == 'F':
        return 'float', pos + 1
    elif ch == 'I':
        return 'int', pos + 1
    elif ch == 'J':
        return 'long', pos + 1
    elif ch == 'S':
        return 'short', pos + 1
    elif ch == 'Z':
        return 'boolean', pos + 1
    elif ch == 'V':
        return 'void', pos + 1
    elif ch == 'L':
        end = desc.index(';', pos)
        fqcn = desc[pos + 1:end].replace('/', '.')
        # Use simple name
        simple = fqcn.rsplit('.', 1)[-1]
        return simple, end + 1
    elif ch == '[':
        inner, new_pos = _decode_type(desc, pos + 1)
        return inner + '[]', new_pos
    else:
        return desc[pos:], len(desc)


def decode_field_type(descriptor: str) -> str:
    """Convert a field descriptor to human-readable type name."""
    t, _ = _decode_type(descriptor, 0)
    return t


def decode_method_signature(name: str, descriptor: str) -> str:
    """Convert a method name + descriptor to a human-readable signature.

    E.g. "setMapping", "(Lcom/intellij/psi/PsiFile;Ljava/lang/String;)V"
       → "void setMapping(PsiFile, String)"
    """
    if not descriptor.startswith('('):
        return f"{name}({descriptor})"

    # Parse parameters
    pos = 1  # skip '('
    params = []
    while pos < len(descriptor) and descriptor[pos] != ')':
        t, pos = _decode_type(descriptor, pos)
        params.append(t)

    # Parse return type
    pos += 1  # skip ')'
    ret, _ = _decode_type(descriptor, pos)

    param_str = ', '.join(params)
    return f"{ret} {name}({param_str})"


# ── Class File Parser ─────────────────────────────────────────────────────

class ClassInfo:
    """Parsed information from a .class file."""
    __slots__ = (
        'access_flags', 'this_class', 'super_class',
        'interfaces', 'fields', 'methods'
    )

    def __init__(self):
        self.access_flags: int = 0
        self.this_class: str = ''
        self.super_class: Optional[str] = None
        self.interfaces: list[str] = []
        self.fields: list[tuple[str, str, str, int, bool]] = []   # (name, descriptor, type_name, flags, is_static)
        self.methods: list[tuple[str, str, str, int, bool]] = []  # (name, descriptor, signature, flags, is_static)


def parse_class(data: bytes) -> Optional[ClassInfo]:
    """Parse a .class file's bytes and return a ClassInfo, or None on error."""
    try:
        return _parse_class_impl(data)
    except (struct.error, IndexError, ValueError, UnicodeDecodeError):
        return None


def _parse_class_impl(data: bytes) -> Optional[ClassInfo]:
    pos = 0

    # Magic number
    magic, = struct.unpack_from('>I', data, pos)
    if magic != 0xCAFEBABE:
        return None
    pos += 4

    # Version (skip)
    pos += 4  # minor + major

    # ── Constant Pool ──
    cp_count, = struct.unpack_from('>H', data, pos)
    pos += 2

    # Index 0 is unused; entries are 1..cp_count-1
    cp = [None] * cp_count  # type: list

    i = 1
    while i < cp_count:
        tag = data[pos]
        pos += 1

        if tag == CP_UTF8:
            length, = struct.unpack_from('>H', data, pos)
            pos += 2
            cp[i] = ('utf8', data[pos:pos + length].decode('utf-8', errors='replace'))
            pos += length
        elif tag == CP_INTEGER:
            cp[i] = ('int',)
            pos += 4
        elif tag == CP_FLOAT:
            cp[i] = ('float',)
            pos += 4
        elif tag == CP_LONG:
            cp[i] = ('long',)
            pos += 8
            i += 1  # longs take two slots
        elif tag == CP_DOUBLE:
            cp[i] = ('double',)
            pos += 8
            i += 1  # doubles take two slots
        elif tag == CP_CLASS:
            name_idx, = struct.unpack_from('>H', data, pos)
            pos += 2
            cp[i] = ('class', name_idx)
        elif tag == CP_STRING:
            pos += 2
            cp[i] = ('string',)
        elif tag in (CP_FIELDREF, CP_METHODREF, CP_INTERFACE_METHODREF):
            pos += 4
            cp[i] = ('ref',)
        elif tag == CP_NAME_AND_TYPE:
            name_idx, desc_idx = struct.unpack_from('>HH', data, pos)
            pos += 4
            cp[i] = ('nat', name_idx, desc_idx)
        elif tag == CP_METHOD_HANDLE:
            pos += 3
            cp[i] = ('mh',)
        elif tag == CP_METHOD_TYPE:
            pos += 2
            cp[i] = ('mt',)
        elif tag in (CP_DYNAMIC, CP_INVOKE_DYNAMIC):
            pos += 4
            cp[i] = ('dyn',)
        elif tag == CP_MODULE:
            pos += 2
            cp[i] = ('module',)
        elif tag == CP_PACKAGE:
            pos += 2
            cp[i] = ('package',)
        else:
            # Unknown tag — bail
            return None

        i += 1

    def get_utf8(idx: int) -> str:
        entry = cp[idx]
        if entry and entry[0] == 'utf8':
            return entry[1]
        return ''

    def get_class_name(idx: int) -> Optional[str]:
        entry = cp[idx]
        if entry and entry[0] == 'class':
            return get_utf8(entry[1]).replace('/', '.')
        return None

    # ── Class Header ──
    access_flags, this_idx, super_idx = struct.unpack_from('>HHH', data, pos)
    pos += 6

    info = ClassInfo()
    info.access_flags = access_flags
    info.this_class = get_class_name(this_idx) or ''
    info.super_class = get_class_name(super_idx) if super_idx != 0 else None

    # ── Interfaces ──
    iface_count, = struct.unpack_from('>H', data, pos)
    pos += 2
    for _ in range(iface_count):
        iface_idx, = struct.unpack_from('>H', data, pos)
        pos += 2
        name = get_class_name(iface_idx)
        if name:
            info.interfaces.append(name)

    # ── Fields ──
    field_count, = struct.unpack_from('>H', data, pos)
    pos += 2
    for _ in range(field_count):
        f_flags, name_idx, desc_idx, attr_count = struct.unpack_from('>HHHH', data, pos)
        pos += 8
        # Skip attributes
        for _ in range(attr_count):
            pos += 2  # attr name index
            attr_len, = struct.unpack_from('>I', data, pos)
            pos += 4 + attr_len

        # Filter: public/protected only, skip synthetic
        if not (f_flags & (ACC_PUBLIC | ACC_PROTECTED)):
            continue
        if f_flags & ACC_SYNTHETIC:
            continue

        fname = get_utf8(name_idx)
        fdesc = get_utf8(desc_idx)
        ftype = decode_field_type(fdesc)
        is_static = bool(f_flags & ACC_STATIC)
        info.fields.append((fname, fdesc, ftype, f_flags, is_static))

    # ── Methods ──
    method_count, = struct.unpack_from('>H', data, pos)
    pos += 2
    for _ in range(method_count):
        m_flags, name_idx, desc_idx, attr_count = struct.unpack_from('>HHHH', data, pos)
        pos += 8
        # Skip attributes
        for _ in range(attr_count):
            pos += 2
            attr_len, = struct.unpack_from('>I', data, pos)
            pos += 4 + attr_len

        # Filter: public/protected only, skip synthetic/bridge, skip <clinit>
        if not (m_flags & (ACC_PUBLIC | ACC_PROTECTED)):
            continue
        if m_flags & (ACC_SYNTHETIC | ACC_BRIDGE):
            continue
        mname = get_utf8(name_idx)
        if mname == '<clinit>':
            continue

        mdesc = get_utf8(desc_idx)
        sig = decode_method_signature(mname, mdesc)
        is_static = bool(m_flags & ACC_STATIC)
        info.methods.append((mname, mdesc, sig, m_flags, is_static))

    return info
