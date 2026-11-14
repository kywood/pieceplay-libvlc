#!/usr/bin/env python3
"""Compare a rebuilt PiecePlay LibVLC AAR with a released one.

usage: python3 -I buildsystem/pieceplay-compare-aar.py <reference.aar> <rebuilt.aar> [--require-identical-native]

Checks (any failure exits with status 1):
  1. Both AARs contain the same entries, and neither ships assets/lua/.
  2. Every entry other than the native libraries, classes.jar and
     res/values/values.xml is byte-identical.
  3. res/values/values.xml differs at most in build_libvlc_revision and
     build_vlc_revision (the commit hashes of the two checkouts).
  4. classes.jar holds the same classes, and `javap -p` (every member,
     private included) prints the same output for each class. Skipped with
     a warning when javap is not on PATH.
  5. Native libraries are listed with their size and SHA-256. They are only
     required to be identical with --require-identical-native, because the
     released 3.7.5-lgpl.1 was built before the build dates were pinned.

The report is Markdown on stdout, so it can go straight to
$GITHUB_STEP_SUMMARY. The GPL scan (libvlc_gpl_scan.py) is a separate step.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REVISION_LINE = re.compile(rb'<string name="build_(libvlc|vlc)_revision"[^>]*>[^<]*</string>')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def is_native(name):
    return name.startswith("jni/") and name.endswith(".so")


def javap_dump(jar_bytes, workdir, tag):
    """Return {class name: javap -p output} or None when javap is missing."""
    javap = shutil.which("javap")
    if javap is None:
        return None
    jar_path = os.path.join(workdir, f"{tag}-classes.jar")
    with open(jar_path, "wb") as fh:
        fh.write(jar_bytes)
    with zipfile.ZipFile(jar_path) as z:
        classes = sorted(n[:-6].replace("/", ".") for n in z.namelist() if n.endswith(".class"))
    out = {}
    for start in range(0, len(classes), 100):
        batch = classes[start:start + 100]
        text = subprocess.run([javap, "-p", "-cp", jar_path, *batch], check=True,
                              capture_output=True, text=True).stdout
        # javap prints one block per class, each starting with "Compiled from".
        blocks = re.split(r"(?m)^(?=Compiled from )", text)
        blocks = [b for b in blocks if b.strip()]
        if len(blocks) != len(batch):
            raise RuntimeError(f"javap returned {len(blocks)} blocks for {len(batch)} classes")
        out.update(zip(batch, blocks))
    return out


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    require_identical_native = "--require-identical-native" in argv
    if len(args) != 2:
        print(__doc__)
        return 2
    ref_path, new_path = args
    failures = []
    lines = ["## AAR comparison", "",
             f"- reference: `{os.path.basename(ref_path)}` sha256 `{sha256(open(ref_path, 'rb').read())}`",
             f"- rebuilt: `{os.path.basename(new_path)}` sha256 `{sha256(open(new_path, 'rb').read())}`", ""]

    with zipfile.ZipFile(ref_path) as rz, zipfile.ZipFile(new_path) as nz:
        ref = {n: rz.read(n) for n in rz.namelist() if not n.endswith("/")}
        new = {n: nz.read(n) for n in nz.namelist() if not n.endswith("/")}

    # 1. entry list
    only_ref = sorted(set(ref) - set(new))
    only_new = sorted(set(new) - set(ref))
    lua = sorted(n for n in set(ref) | set(new) if n.startswith("assets/lua/"))
    if only_ref or only_new:
        failures.append("entry lists differ")
    if lua:
        failures.append("assets/lua/ present")
    lines.append(f"### 1. Entries: {len(ref)} reference / {len(new)} rebuilt")
    lines += [f"- only in reference: `{n}`" for n in only_ref]
    lines += [f"- only in rebuilt: `{n}`" for n in only_new]
    lines += [f"- Lua script shipped: `{n}`" for n in lua]
    lines.append("")

    common = sorted(set(ref) & set(new))

    # 2. plain files
    plain = [n for n in common if not is_native(n) and n not in ("classes.jar", "res/values/values.xml")]
    differing = [n for n in plain if ref[n] != new[n]]
    if differing:
        failures.append("non-native files differ")
    lines.append(f"### 2. Other files: {len(plain) - len(differing)}/{len(plain)} byte-identical")
    lines += [f"- differs: `{n}`" for n in differing]
    lines.append("")

    # 3. values.xml
    if "res/values/values.xml" in common:
        rv, nv = ref["res/values/values.xml"], new["res/values/values.xml"]
        same_rest = REVISION_LINE.sub(b"", rv) == REVISION_LINE.sub(b"", nv)
        if not same_rest:
            failures.append("values.xml differs beyond the revision strings")
        lines.append("### 3. res/values/values.xml")
        for label, data in (("reference", rv), ("rebuilt", nv)):
            revs = [m.group(0).decode() for m in REVISION_LINE.finditer(data)]
            lines.append(f"- {label}: " + ", ".join(f"`{r}`" for r in revs))
        lines.append(f"- rest of the file identical: {'yes' if same_rest else '**no**'}")
        lines.append("")

    # 4. classes.jar
    if "classes.jar" in common:
        lines.append("### 4. classes.jar")
        identical = ref["classes.jar"] == new["classes.jar"]
        lines.append(f"- byte-identical: {'yes' if identical else 'no'}")
        if not identical:
            with tempfile.TemporaryDirectory() as tmp:
                rd = javap_dump(ref["classes.jar"], tmp, "ref")
                nd = javap_dump(new["classes.jar"], tmp, "new")
            if rd is None:
                lines.append("- javap not found: member comparison skipped (warning)")
            else:
                changed = sorted(c for c in set(rd) | set(nd) if rd.get(c) != nd.get(c))
                if changed:
                    failures.append("classes.jar members differ")
                lines.append(f"- classes: {len(rd)} reference / {len(nd)} rebuilt, "
                             f"`javap -p` identical for {len(set(rd) & set(nd)) - len(changed)}")
                lines += [f"- members differ: `{c}`" for c in changed]
        lines.append("")

    # 5. native libraries
    natives = [n for n in common if is_native(n)]
    same_native = 0
    lines += ["### 5. Native libraries", "",
              "| file | reference size | rebuilt size | identical | rebuilt sha256 |",
              "|---|---:|---:|---|---|"]
    for n in natives:
        same = ref[n] == new[n]
        same_native += same
        lines.append(f"| `{n}` | {len(ref[n]):,} | {len(new[n]):,} | {'yes' if same else 'no'} | `{sha256(new[n])}` |")
    lines.append("")
    lines.append(f"{same_native}/{len(natives)} native libraries byte-identical.")
    if require_identical_native and same_native != len(natives):
        failures.append("native libraries differ (--require-identical-native)")
    lines.append("")

    lines.append("### Result: " + ("**FAIL** - " + "; ".join(failures) if failures else "**PASS**"))
    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
