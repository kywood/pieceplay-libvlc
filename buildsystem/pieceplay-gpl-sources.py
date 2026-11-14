#!/usr/bin/env python3
"""Fail when a GPL-only source file was linked into a shared library.

usage: python3 -I buildsystem/pieceplay-gpl-sources.py [--map OLD=NEW] <unstripped .so> [<report.tsv>]

--map rewrites the path prefix recorded at build time (for example /work=/home/me/checkout when the
library was built in the Docker container and is checked on the host).

The library must still have its DWARF (the unstripped copy that ndk-build keeps in
libvlc/jni/obj/local/<abi>/). For every compilation unit (DW_AT_comp_dir + DW_AT_name) whose
source file is still on disk (VLC, contrib and libvlcjni sources stay in the build tree), the
first 6000 bytes are read and classified:

  gpl        GNU GPL text, no LGPL grant, no exception and no permissive alternative
  dual       GPL offered as one choice among others (SPDX "OR", BSD redistribution text,
             Apache License), e.g. Mbed TLS "Apache-2.0 OR GPL-2.0-or-later"
  mixed      a GPL grant sentence together with an LGPL grant sentence (needs a person)
  exception  GPL text with a linking exception (Bison parser skeleton, GCC runtime)
  other      no GPL text, or an LGPL grant with the GPL only named in the boilerplate

Both licences are recognised by their grant sentence ("terms of the GNU General Public License",
"terms of the GNU Lesser/Library General Public License", or an SPDX identifier), not by the word
"LGPL", which a GPL-only file can also contain. A header that names the GPL without any LGPL
grant is "gpl" (or "dual") even when it has no GPL grant sentence either. The exit status is 1 for any "gpl" file and for any "dual" or "mixed" file that is not
in ALLOWED. "exception" files and the allowed ones are listed for review.
Compilation units without DWARF (contribs built without -g) and missing files are counted
and reported, so the coverage of the check is visible; buildsystem/libvlc_gpl_scan.py and
the contrib library check in compile-libvlc.sh cover the rest.
"""
import os
import re
import subprocess
import sys

# The header is matched after comment leaders and line breaks are folded into single spaces,
# so a licence sentence split over several comment lines still matches.
FOLD = re.compile(rb"(?:[\s*#;/!]|\\)+")
# Any mention of the GPL: the GNU GPL by name (the LGPL names never contain "GNU General Public
# License"), a GPL SPDX identifier, or the usual short forms.
GPL = re.compile(rb"GNU General Public License|SPDX-License-Identifier: \(?(?:GPL|AGPL)-[23]|"
                 rb"\bGPL ?v?[23]\b|\bGPL-[23]\.0", re.I)
# A GPL grant: the licence sentence itself. LGPL headers often say "See the GNU General Public
# License for more details" or "You should have received a copy of the GNU General Public
# License" by mistake; those sentences are not a grant.
GPL_GRANT = re.compile(rb"terms of the GNU General Public License|under the GNU General Public License|"
                       rb"licen[cs]ed under the GPL|SPDX-License-Identifier: \(?(?:GPL|AGPL)-[23]", re.I)
# LGPL grant: the licence sentence itself, not just the word "LGPL" somewhere in the header
# (an "LGPL" in a comment let a GPL-only FFmpeg filter through the old check).
LGPL = re.compile(rb"terms of the GNU (?:Lesser|Library) General Public License|"
                  rb"under the GNU (?:Lesser|Library) General Public License|"
                  rb"SPDX-License-Identifier: \(?LGPL-", re.I)
ALTERNATIVE = re.compile(rb"SPDX-License-Identifier: [^()]*\bOR\b|Redistribution and use in source and binary forms|"
                         rb"Apache License|at your option[^.]*(?:BSD|MIT)", re.I)
# GPL files found in otherwise LGPL contribs. Always "gpl", whatever their header says, so a
# change of the header heuristics can never let them through. Paths are suffixes of the
# compilation unit path. 3.7.5-lgpl.1/.2 linked zvbi packet-830.c (all ABIs) and the three
# FFmpeg files (arm64); zvbi pdc.c was in libzvbi.a but not linked. 3.7.5-lgpl.3 removes them.
KNOWN_GPL = (
    "/zvbi/src/packet-830.c",                              # zvbi 0.2.44 COPYING.md: GPL-2
    "/zvbi/src/pdc.c",                                     # zvbi 0.2.44 COPYING.md: GPL-2
    "/ffmpeg/libavcodec/aarch64/ac3dsp_init_aarch64.c",    # FFmpeg 8.1.2 header: GPL-2.0-or-later
    "/ffmpeg/libavcodec/aarch64/ac3dsp_neon.S",            # FFmpeg 8.1.2 header: GPL-2.0-or-later
    "/ffmpeg/libavutil/aarch64/crc.S",                     # FFmpeg 8.1.2 header: GPL-2.0-or-later
)

# GPL text with a linking exception that lets the output be distributed under other terms
# (Bison parser skeleton, GCC runtime library). Allowed, and listed.
EXCEPTION = re.compile(rb"As a special exception, you may create a larger work|GCC Runtime Library Exception", re.I)

# Files that were reviewed and may be linked although their header names the GPL. Each entry is a
# path suffix and the reason; anything "dual" or "mixed" that is not listed fails the build.
ALLOWED = {
    "dual": {
        "/gcrypt/random/rndjent.c":
            "libgcrypt jitterentropy: BSD-3-Clause, or GPL instead of it at the user's choice",
    },
    "mixed": {
        "/libgpg-error/src/estream.c":
            "libestream: LGPL-2.1-or-later, ALTERNATIVELY a BSD-style licence; the GPL is only named in "
            "the BSD alternative clause",
        "/libgpg-error/src/estream-printf.c":
            "libestream: LGPL-2.1-or-later, ALTERNATIVELY a BSD-style licence; the GPL is only named in "
            "the BSD alternative clause",
        # x86_64 only
        "/gcrypt/cipher/keccak-amd64-avx512.S":
            "libgcrypt part LGPL-2.1-or-later; the KeccakF1600 core is CRYPTOGAMS BSD-3-Clause, which "
            "may ALTERNATIVELY be distributed under the GPL (libgcrypt LICENSES lists the file as CRYPTOGAMS)",
    },
}


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
    """gpl, dual, mixed, exception or other (see the module documentation)."""
    with open(path, "rb") as fh:
        head = FOLD.sub(b" ", fh.read(6000))
    gpl, grant, lgpl = GPL.search(head), GPL_GRANT.search(head), LGPL.search(head)
    if not gpl:
        return "other"
    if EXCEPTION.search(head):
        return "exception"
    if grant and lgpl:
        return "mixed"
    if lgpl:
        # LGPL grant, GPL only named in the boilerplate (no GPL grant sentence)
        return "other"
    # GPL named and no LGPL grant: GPL unless a permissive alternative is offered
    return "dual" if ALTERNATIVE.search(head) else "gpl"


def allowed(kind, path):
    return any(path.endswith(suffix) for suffix in ALLOWED.get(kind, {}))


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

    found = {"gpl": [], "dual": [], "mixed": [], "exception": [], "other": [], "missing": []}
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
    failed = [("GPL source linked", f) for f in found["gpl"]]
    for kind in ("dual", "mixed"):
        failed += [(f"{kind} source not in the allowed list", f) for f in found[kind] if not allowed(kind, f)]
    print(f"GPL source check: {so}: {len(units)} compilation units, {len(found['other'])} non-GPL, "
          f"{len(found['dual'])} dual-licensed, {len(found['mixed'])} mixed, "
          f"{len(found['exception'])} GPL with exception, {len(found['missing'])} not on disk, "
          f"{len(found['gpl'])} GPL")
    for kind in ("dual", "mixed", "exception"):
        for f in found[kind]:
            ok = kind == "exception" or allowed(kind, f)
            print(f"[{kind}{'' if ok else ', not allowed'}] {f}")
    for reason, f in failed:
        print(f"[FAIL] {reason}: {f}")
    if not units:
        print("[FAIL] no DWARF compilation units: pass the unstripped library")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
