#!/usr/bin/env python3
"""Build and assemble a fresh public package. No development binaries or game data.

Never reuses/deletes a destination, reads a player save, or copies from dist.
Validation is mandatory before and after copying the allowlisted files.
"""
import argparse
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

from release_gate import ARTIFACTS, validate_build, validate_package

HERE = Path(__file__).resolve().parent


from build import SDL_UNIX_LIBRARY, UNIX_LAUNCHER_SUFFIX, sdl2_unix_flags, sdl2_unix_library

UNIX_ARTIFACTS = ("moonstone", f"Moonstone Singleplayer{UNIX_LAUNCHER_SUFFIX}",
                  f"Moonstone Multiplayer{UNIX_LAUNCHER_SUFFIX}")


def unix_package_name():
    system = {"darwin": "macOS", "linux": "Linux"}.get(sys.platform, sys.platform)
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64"}.get(
        platform.machine().lower(), platform.machine().lower())
    return f"Moonstone-2026-{system}-{arch}"


def unix_dependencies(path):
    """Shared libraries a binary loads: (install name or soname, ...)."""
    if sys.platform == "darwin":
        lines = subprocess.run(["otool", "-L", str(path)], check=True, capture_output=True,
                               text=True).stdout.splitlines()[1:]
        return [line.split(" (")[0].strip() for line in lines]
    dynamic = subprocess.run(["readelf", "-d", str(path)], check=True, capture_output=True,
                             text=True).stdout
    return [line.split("[")[1].split("]")[0] for line in dynamic.splitlines() if "(NEEDED)" in line]


def system_library(name):
    if sys.platform == "darwin":
        return name.startswith(("/System/Library/", "/usr/lib/"))
    return name.split(".so")[0] in ("libc", "libm", "libdl", "libpthread", "librt",
                                    "ld-linux-x86-64", "ld-linux-aarch64")


def bundle_sdl2(out):
    """Copies SDL2 next to moonstone and makes the binary load that copy, so
    players need no SDL2 install. Refuses libraries that would need more than
    the operating system (sdl2-compat's SDL3, distribution SDL2's X11/Pulse)."""
    library = sdl2_unix_library(sdl2_unix_flags()[1])
    extra = [d for d in unix_dependencies(library)
             if not system_library(d) and Path(d).name != SDL_UNIX_LIBRARY]
    if extra or b"sdl2-compat" in library.read_bytes():
        raise SystemExit(f"{library} is not self-contained ({extra or 'sdl2-compat'}); "
                         "run unix/build-sdl2.sh to build a bundleable SDL2")
    bundled = out / SDL_UNIX_LIBRARY
    shutil.copyfile(library, bundled)  # resolves the soname symlink to the real file
    bundled.chmod(0o755)
    binary = out / "moonstone"
    if sys.platform == "darwin":
        linked = [d for d in unix_dependencies(binary) if Path(d).name == SDL_UNIX_LIBRARY]
        if len(linked) != 1:
            raise SystemExit(f"moonstone does not link one {SDL_UNIX_LIBRARY}: {linked}")
        name = f"@executable_path/{SDL_UNIX_LIBRARY}"
        subprocess.run(["install_name_tool", "-id", name, str(bundled)], check=True)
        subprocess.run(["install_name_tool", "-change", linked[0], name, str(binary)], check=True)
        for path in (bundled, binary):  # install_name_tool invalidates the signature
            subprocess.run(["codesign", "--force", "--sign", "-", str(path)], check=True)
    else:
        runpath = subprocess.run(["readelf", "-d", str(binary)], check=True,
                                 capture_output=True, text=True).stdout
        if "[$ORIGIN]" not in runpath:
            raise SystemExit("moonstone has no $ORIGIN runpath; rebuild with build.py")
    extra = [d for d in unix_dependencies(binary)
             if not system_library(d) and d not in (SDL_UNIX_LIBRARY, f"@executable_path/{SDL_UNIX_LIBRARY}")]
    if extra:
        raise SystemExit(f"moonstone needs libraries outside the package: {extra}")


def package_unix(out):
    """macOS/Linux: release build, exact file allowlist, portable folder + tar.gz.
    The Windows PE/launcher-hash gate does not apply to these binaries."""
    subprocess.run([sys.executable, str(HERE / "build.py"), "--profile", "release"], check=True)
    build = HERE / "build/release"
    sources = {name: build / name for name in UNIX_ARTIFACTS}
    sources.update({"controls.ini": HERE / "controls.ini", "README.txt": HERE / "unix/README.txt",
                    "RELEASE-NOTES.md": HERE.parent / "RELEASE-NOTES.md",
                    "LICENSE.txt": HERE.parent / "LICENSE",
                    "THIRD-PARTY-NOTICES.txt": HERE.parent / "THIRD-PARTY-NOTICES.txt",
                    "data/PLACE_ADF_FILES_HERE.txt": HERE / "PLACE_ADF_FILES_HERE.txt"})
    for source in sources.values():
        if not source.is_file():
            raise FileNotFoundError(source)
    out.mkdir(parents=True, exist_ok=False)
    for name in ("data", "saves/Singleplayer", "saves/Multiplayer"):
        (out / name).mkdir(parents=True)
    for name, source in sources.items():
        shutil.copy2(source, out / name)
    bundle_sdl2(out)
    sources[SDL_UNIX_LIBRARY] = None
    found = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    if found != set(sources):
        raise SystemExit(f"package allowlist mismatch: {sorted(found ^ set(sources))}")
    archive = out.with_name(out.name + ".tar.gz")
    if archive.exists():
        raise SystemExit(f"refusing to overwrite existing archive: {archive}")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(out, arcname=out.name)  # keeps the executable bits and empty save folders
    print(f"Package ready: {out}\nArchive: {archive}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    unix = sys.platform != "win32"
    ap.add_argument("output", nargs="?", type=Path,
                    default=HERE.parent / "dist/release-staging" /
                    (unix_package_name() if unix else "Moonstone-2026-Windows-x64"))
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        ap.error(f"refusing to reuse existing staging folder: {out}")
    if unix:
        package_unix(out)
        return
    subprocess.run([sys.executable, str(HERE / "build.py"), "--profile", "release"], check=True)
    build = HERE / "build/release"
    validate_build(build)
    sources = {name: build / name for name in ARTIFACTS}
    sources.update({"controls.ini": HERE / "controls.ini", "README.txt": HERE / "dist_README.txt",
                    "RELEASE-NOTES.md": HERE.parent / "RELEASE-NOTES.md",
                    "LICENSE.txt": HERE.parent / "LICENSE",
                    "THIRD-PARTY-NOTICES.txt": HERE.parent / "THIRD-PARTY-NOTICES.txt",
                    "data/PLACE_ADF_FILES_HERE.txt": HERE / "PLACE_ADF_FILES_HERE.txt"})
    for source in sources.values():
        if not source.is_file():
            raise FileNotFoundError(source)
    out.mkdir(parents=True, exist_ok=False)
    for name in ("data", "saves/Singleplayer", "saves/Multiplayer"):
        (out / name).mkdir(parents=True)
    for name, source in sources.items():
        shutil.copy2(source, out / name)
    validate_package(out, build)
    print(f"Public release package verified: {out}")


if __name__ == "__main__":
    main()
