#!/usr/bin/env python3
"""Fail when a GPL-only source file was linked into a shared library.

usage: python3 -I buildsystem/pieceplay-gpl-sources.py [--map OLD=NEW] <unstripped .so> [<report.tsv>]

--map rewrites the path prefix recorded at build time (for example /work=/home/me/checkout when the
library was built in the Docker container and is checked on the host).

The library must still have its DWARF (the unstripped copy that ndk-build keeps in
libvlc/jni/obj/local/<abi>/). For every compilation unit (DW_AT_comp_dir + DW_AT_name) whose
source file is still on disk (VLC, contrib and libvlcjni sources stay in the build tree), the
first 6000 bytes are read and classified:

  gpl     GNU GPL text and no LGPL / Library GPL text, and no permissive alternative
  dual    GPL offered as one choice among others (SPDX "OR", BSD redistribution text,
          Apache License), e.g. Mbed TLS "Apache-2.0 OR GPL-2.0-or-later"
  exception  GPL text with a linking exception (Bison parser skeleton, GCC runtime)
  other   everything else (LGPL, BSD, MIT, ...)

Any "gpl" file makes the script exit with status 1. "dual" and "exception" files are listed for review.
Compilation units without DWARF (contribs built without -g) and missing files are counted
and reported, so the coverage of the check is visible; buildsystem/libvlc_gpl_scan.py and
the contrib library check in compile-libvlc.sh cover the rest.
"""
import os
import re
import subprocess
import sys

GPL = re.compile(rb"GNU General Public License|General Public License as published|GPL-2\.0|GPL-3\.0|GPLv[23]", re.I)
LGPL = re.compile(rb"Lesser General Public|Library General Public|LGPL", re.I)
ALTERNATIVE = re.compile(rb"SPDX-License-Identifier:[^\n]*\bOR\b|Redistribution and use in source and binary forms|"
                         rb"Apache License|at your option[^\n]*(?:BSD|MIT)", re.I)
# GPL files found in otherwise LGPL contribs. Always "gpl", whatever their header says, so a
# change of the header heuristics can never let them through. Paths are suffixes of the
# compilation unit path. (3.7.5-lgpl.1/.2 linked all of them; 3.7.5-lgpl.3 removes them.)
KNOWN_GPL = (
    "/zvbi/src/packet-830.c",                              # zvbi 0.2.44 COPYING.md: GPL-2
    "/zvbi/src/pdc.c",                                     # zvbi 0.2.44 COPYING.md: GPL-2
    "/ffmpeg/libavcodec/aarch64/ac3dsp_init_aarch64.c",    # FFmpeg 8.1.2 header: GPL-2.0-or-later
    "/ffmpeg/libavcodec/aarch64/ac3dsp_neon.S",            # FFmpeg 8.1.2 header: GPL-2.0-or-later
    "/ffmpeg/libavutil/aarch64/crc.S",                     # FFmpeg 8.1.2 header: GPL-2.0-or-later
)

# GPL text with a linking exception that lets the output be distributed under other terms
# (Bison parser skeleton, GCC runtime library). Reported apart from "dual".
EXCEPTION = re.compile(rb"As a special exception, you may create a larger work|GCC Runtime Library Exception", re.I)


def compilation_units(so):
    out = subprocess.run(["readelf", "--debug-dump=info", "--dwarf-depth=1", so],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    units, name, comp = [], None, None
    for line in out.splitlines():
        if "DW_TAG_compile_unit" in line:
            if name:
                units.append(os.path.normpath(os.path.join(comp or "", name)))
            name = comp = None
            continue
        m = re.search(r"DW_AT_name\s*:\s*(?:\(.*?\):\s*)?(.+)$", line)
        if m and name is None:
            name = m.group(1).strip()
        m = re.search(r"DW_AT_comp_dir\s*:\s*(?:\(.*?\):\s*)?(.+)$", line)
        if m:
            comp = m.group(1).strip()
    if name:
        units.append(os.path.normpath(os.path.join(comp or "", name)))
    return sorted(set(units))


def classify(path):
    with open(path, "rb") as fh:
        head = fh.read(6000)
    if GPL.search(head) and not LGPL.search(head):
        if EXCEPTION.search(head):
            return "exception"
        return "dual" if ALTERNATIVE.search(head) else "gpl"
    return "other"


def main(argv):
    args = list(argv[1:])
    mapping = None
    if len(args) >= 2 and args[0] == "--map":
        old, new = args[1].split("=", 1)
        mapping = (old.rstrip("/") + "/", new.rstrip("/") + "/")
        args = args[2:]
    if not args:
        print(__doc__)
        return 2
    so = args[0]
    units = compilation_units(so)
    def remap(path):
        if mapping and path.startswith(mapping[0]):
            return mapping[1] + path[len(mapping[0]):]
        return path

    found = {"gpl": [], "dual": [], "exception": [], "other": [], "missing": []}
    for unit in units:
        path = remap(unit)
        if not os.path.isfile(path):
            # FFmpeg builds out of tree through a "src" symlink that points at the build-time path
            path = remap(os.path.realpath(path))
        known = [p for p in (unit, path, unit.replace("/vlc_build/src/", "/")) if p.endswith(KNOWN_GPL)]
        if known:
            found["gpl"].append(path)
        elif os.path.isfile(path):
            found[classify(path)].append(path)
        else:
            found["missing"].append(path)
    if len(args) > 1:
        with open(args[1], "w") as fh:
            for kind, files in found.items():
                for f in files:
                    fh.write(f"{kind}\t{f}\n")
    print(f"GPL source check: {so}: {len(units)} compilation units, {len(found['other'])} non-GPL, "
          f"{len(found['dual'])} dual-licensed, {len(found['exception'])} GPL with exception, "
          f"{len(found['missing'])} not on disk, {len(found['gpl'])} GPL")
    for kind in ("dual", "exception"):
        for f in found[kind]:
            print(f"[{kind}] {f}")
    for f in found["gpl"]:
        print(f"[FAIL] GPL source linked: {f}")
    if not units:
        print("[FAIL] no DWARF compilation units: pass the unstripped library")
        return 1
    return 1 if found["gpl"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
