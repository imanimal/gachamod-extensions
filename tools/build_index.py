#!/usr/bin/env python3
"""Zip every package in packages/ into dist/ and write index.json, the list gachamod reads.

Run from anywhere: python tools/build_index.py. With --check it only checks the packages (for pull requests).
The same checks run in gachamod when a package is installed, so a package that passes here installs there.
Zips are built the same way every time (sorted names, fixed dates), so an unchanged package keeps its checksum.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = os.environ.get("PACKAGE_BASE_URL", "https://raw.githubusercontent.com/imanimal/gachamod-extensions/main/")
SUBMIT_URL = os.environ.get("SUBMIT_URL", "https://github.com/imanimal/gachamod-extensions/issues/new?template=submit.yml")
MAX_ZIP = 20 * 1024 * 1024
SKIP = {".git", ".gitignore", "node_modules", ".DS_Store", "Thumbs.db", "desktop.ini"}

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,38}[a-z0-9]$")
VERSION = re.compile(r"^v?\d+(\.\d+){0,2}(-[0-9A-Za-z.]+)?(\+.*)?$")
ENV_PATH = re.compile(r"^%(LOCALAPPDATA|APPDATA|USERPROFILE|PROGRAMDATA|PROGRAMFILES|PROGRAMFILES\(X86\)|PUBLIC)%", re.I)


def fail(pkg, msg):
    sys.exit(f"{pkg}: {msg}")


def origin(raw):
    m = re.match(r"^(https?)://([^/?#@]+)", raw.strip(), re.I)
    if not m:
        return None
    scheme, host = m.group(1).lower(), m.group(2).lower()
    name = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
    if scheme == "http" and name not in ("127.0.0.1", "localhost", "[::1]"):
        return None
    return f"{scheme}://{host}"


def files_of(folder):
    out = []
    for base, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith(".git"))
        for n in sorted(names):
            if n in SKIP or n.lower().endswith(".zip"):
                continue
            full = os.path.join(base, n)
            out.append((os.path.relpath(full, folder).replace(os.sep, "/"), full))
    return sorted(out)


def check(pkg, folder):
    path = os.path.join(folder, "extension.json")
    if not os.path.isfile(path):
        fail(pkg, "no extension.json")
    with open(path, encoding="utf-8-sig") as f:
        m = json.load(f)
    if m.get("format", 1) > 1:
        fail(pkg, "format is newer than this script knows")
    if m.get("id") != pkg or not ID.match(pkg):
        fail(pkg, "the id must match the folder name: lower case letters, digits and dashes")
    for key in ("name", "version", "author"):
        if not str(m.get(key, "")).strip():
            fail(pkg, f"{key} is missing")
    if not VERSION.match(m["version"]):
        fail(pkg, f"{m['version']} isn't a version like 1.0.0")
    if len(m.get("description", "")) > 300:
        fail(pkg, "keep the description under 300 characters")
    if not (m.get("themes") or m.get("characterTab") or m.get("page")):
        fail(pkg, "it adds nothing: list themes, a characterTab or a page")
    wanted = list(m.get("themes", []))
    for slot in ("characterTab", "page"):
        if m.get(slot):
            wanted.append(m[slot].get("entry", ""))
    if m.get("icon"):
        wanted.append(m["icon"])
    for rel in wanted:
        if not rel or rel.startswith(("/", "\\")) or ".." in rel.replace("\\", "/").split("/") or not os.path.isfile(os.path.join(folder, rel)):
            fail(pkg, f"{rel!r} is missing")
    perms = m.get("permissions", {})
    net = []
    for o in perms.get("net", []):
        n = origin(o)
        if not n:
            fail(pkg, f"{o} must be an https origin, or http on 127.0.0.1")
        net.append(n)
    for p in perms.get("files", []):
        if not ENV_PATH.match(p) or ".." in p:
            fail(pkg, f"{p} must start with a known folder like %LOCALAPPDATA%")
    for app in m.get("needs", []):
        if not app.get("name"):
            fail(pkg, "every app in needs has a name")
        if app.get("url") and not app["url"].startswith("https://"):
            fail(pkg, f"the link to {app['name']} must be https")
        if app.get("running") and origin(app["running"]) not in net:
            fail(pkg, f"add the origin of {app['running']} to permissions.net")
    m.setdefault("permissions", {})["net"] = net
    return m


def build_zip(folder, out):
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, full in files_of(folder):
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as f:
                z.writestr(info, f.read())
    os.replace(tmp, out)


def updated(folder):
    try:
        t = subprocess.run(["git", "log", "-1", "--format=%ct", "--", folder], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if t:
            return int(t)
    except OSError:
        pass
    return int(max(os.path.getmtime(full) for _, full in files_of(folder)))


def main():
    only_check = "--check" in sys.argv
    pkgs_dir = os.path.join(ROOT, "packages")
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    entries, keep = [], set()
    for pkg in sorted(os.listdir(pkgs_dir)):
        folder = os.path.join(pkgs_dir, pkg)
        if not os.path.isdir(folder):
            continue
        m = check(pkg, folder)
        if only_check:
            print(f"ok  {pkg} {m['version']}")
            continue
        name = f"{pkg}-{m['version']}.zip"
        out = os.path.join(dist, name)
        build_zip(folder, out)
        keep.add(name)
        data = open(out, "rb").read()
        if len(data) > MAX_ZIP:
            fail(pkg, "the zip is over 20 MB")
        perms = m.get("permissions", {})
        entries.append({
            "id": pkg,
            "name": m["name"].strip(),
            "version": m["version"],
            "kind": "extension" if (m.get("characterTab") or m.get("page")) else "theme",
            "author": m["author"].strip(),
            "description": m.get("description", "").strip(),
            "games": m.get("games", []),
            "homepage": m.get("homepage"),
            "icon": BASE_URL + f"packages/{pkg}/{m['icon']}" if m.get("icon") else None,
            "preview": BASE_URL + f"packages/{pkg}/{m['preview']}" if m.get("preview") else None,
            "download": BASE_URL + f"dist/{name}",
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "updated": updated(folder),
            "app": m.get("app"),
            "permissions": {"library": bool(perms.get("library")), "player": bool(perms.get("player")),
                            "net": perms.get("net", []), "files": perms.get("files", [])},
            "needs": [{"name": a["name"], "url": a.get("url"), "required": a.get("required", True)} for a in m.get("needs", [])],
        })
        print(f"built {name}")
    if only_check:
        return
    for old in os.listdir(dist):
        if old.endswith(".zip") and old not in keep:
            os.remove(os.path.join(dist, old))
    index = {"format": 1, "name": "gachamod extensions", "submit": SUBMIT_URL, "packages": entries}
    with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"index.json: {len(entries)} packages")


if __name__ == "__main__":
    main()
