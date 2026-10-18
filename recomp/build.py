#!/usr/bin/env python3
"""Canonical build recipe using Python and the existing Zig/SDL bundle.

Development (default): build/moonstone.exe, with regression/debugging tools.
Release: build/release/moonstone.exe, without those tools or debug metadata.
The package command always selects release and validates its provenance.
On macOS/Linux the same sources build natively with the system C compiler
and SDL2 (build/moonstone, build/release/moonstone); see BUILDING.md.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from release_gate import ARTIFACTS, input_hashes, inspect_pe, sha256, validate_build
from pe_metadata import normalize_file
from engine_icons import store_icons

HERE = Path(__file__).resolve().parent
ZIG = HERE / "tools/zig-x86_64-windows-0.16.0/zig.exe"
MUS = "vendor/Musashi-master"
SDL = "vendor/SDL2"
# Finder opens .command files in Terminal; Linux file managers run .sh files.
UNIX_LAUNCHER_SUFFIX = ".command" if sys.platform == "darwin" else ".sh"


def run(args, cwd=HERE):
    # Keep compiler caches inside this checkout, never borrow another project's.
    env = dict(os.environ, ZIG_LOCAL_CACHE_DIR=str(HERE / "build/zig-local-cache"),
               ZIG_GLOBAL_CACHE_DIR=str(HERE / "build/zig-global-cache"))
    subprocess.run([str(ZIG), *map(str, args)], cwd=cwd, env=env, check=True)


SDL_UNIX = HERE / "vendor/SDL2-unix"  # built by unix/build-sdl2.sh, bundled by package.py
SDL_UNIX_LIBRARY = "libSDL2-2.0.0.dylib" if sys.platform == "darwin" else "libSDL2-2.0.so.0"


def sdl2_unix_flags():
    """SDL2 compile/link flags: the bundleable vendor/SDL2-unix build first,
    then sdl2-config, then pkg-config."""
    tools = [["sdl2-config"], ["pkg-config", "sdl2"]]
    if (SDL_UNIX / "bin/sdl2-config").is_file():
        tools.insert(0, [str(SDL_UNIX / "bin/sdl2-config")])
    for tool in tools:
        if shutil.which(tool[0]):
            cflags = shlex.split(subprocess.run([*tool, "--cflags"], check=True,
                                                capture_output=True, text=True).stdout)
            libs = shlex.split(subprocess.run([*tool, "--libs"], check=True,
                                              capture_output=True, text=True).stdout)
            # The sources include <SDL2/SDL.h>; the tools point inside .../SDL2.
            parents = [f"-I{Path(f[2:]).parent}" for f in cflags
                       if f.startswith("-I") and Path(f[2:]).name == "SDL2"]
            return cflags + parents, libs
    raise SystemExit("SDL2 not found: install it (macOS: brew install sdl2, "
                     "Debian/Ubuntu: sudo apt install libsdl2-dev) and retry")


def sdl2_unix_library(sdl_libs):
    """The SDL2 shared library the build links against (first -L dir that has it)."""
    for flag in sdl_libs:
        if flag.startswith("-L") and (Path(flag[2:]) / SDL_UNIX_LIBRARY).exists():
            return Path(flag[2:]) / SDL_UNIX_LIBRARY
    raise SystemExit(f"{SDL_UNIX_LIBRARY} not found in {' '.join(sdl_libs)}; "
                     "run unix/build-sdl2.sh")


def build_unix(args, dev, out):
    """Native macOS/Linux build: same sources and profiles, system cc + SDL2.
    No Windows resources, PE metadata or launcher EXEs; shell launchers instead."""
    cc = os.environ.get("CC", "cc")

    def run_cc(cmd, cwd=HERE):
        subprocess.run([cc, *map(str, cmd)], cwd=cwd, check=True)

    if not (HERE / MUS / "m68kops.c").is_file():
        run_cc(["-O2", "-o", f"{MUS}/m68kmake", f"{MUS}/m68kmake.c"])
        subprocess.run([str(HERE / MUS / "m68kmake")], cwd=HERE / MUS, check=True)
    sdl_cflags, sdl_libs = sdl2_unix_flags()
    sources = [str(args.probe.resolve()) if args.probe else "src/moon.c", "src/loader.c",
               f"{MUS}/m68kcpu.c", f"{MUS}/m68kops.c", f"{MUS}/softfloat/softfloat.c"]
    if dev:
        sources.append(f"{MUS}/m68kdasm.c")
    flags = ["-O2", "-std=c11", f"-DMOON_DEVELOPER={int(dev)}",
             "-DMUSASHI_CNF=\"m68kconf_moon.h\"", "-Iunix",
             f"-I{MUS}", f"-I{MUS}/softfloat", "-Isrc", *sdl_cflags,
             "-Wno-unused-parameter", "-Wno-unused-but-set-variable", "-Wno-unused-function",
             "-Wno-date-time"]
    if args.typecheck:
        checkdir = HERE / "build/typecheck" / args.profile
        checkdir.mkdir(parents=True, exist_ok=True)
        for index, source in enumerate(sources):
            run_cc([*flags, "-c", source, "-o", checkdir / f"source-{index}.o"])
        print(f"C typecheck passed ({args.profile})")
        return
    if not dev:
        # Release binaries load the SDL2 bundled next to them, never a build path.
        sdl_libs = [f for f in sdl_libs if not f.startswith("-Wl,-rpath")]
    if sys.platform != "darwin":
        # package.py bundles libSDL2-2.0.so.0 next to the binary.
        sdl_libs = ["-Wl,-rpath,$ORIGIN", *sdl_libs]
    run_cc([*flags, "-g" if dev else "-g0", *sources, *sdl_libs, "-lm", "-o", out / args.target])
    if not dev:
        subprocess.run(["strip", str(out / args.target)], check=True)  # no symbols in release
    if args.probe:
        print(f"Built TEST ONLY: {out / args.target}")
        return
    for profile in ("Singleplayer", "Multiplayer"):
        launcher = out / f"Moonstone {profile}{UNIX_LAUNCHER_SUFFIX}"
        shutil.copy2(HERE / "unix" / f"Moonstone {profile}.sh", launcher)
        launcher.chmod(0o755)
    print(f"Built {args.profile}: {out / args.target}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", default="moonstone")
    ap.add_argument("--profile", choices=("development", "release"), default="development")
    ap.add_argument("--probe", type=Path, help="test-only source including moon.c; never package this output")
    ap.add_argument("--typecheck", action="store_true", help="C syntax/type check only")
    args = ap.parse_args()
    if not args.target.replace("-", "").replace("_", "").isalnum():
        ap.error("target must be a simple executable name")
    if args.probe and args.target == "moonstone":
        ap.error("a test probe must have its own target name")
    dev = args.profile == "development"
    out = HERE / ("build" if dev else "build/release")
    out.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        build_unix(args, dev, out)
        return
    manifest = out / "release-build.json"
    if not dev and not args.probe and not args.typecheck:
        manifest.unlink(missing_ok=True)  # A failed build cannot leave stale approval.
    if not (HERE / MUS / "m68kops.c").is_file():
        run(["cc", "-O2", "-o", f"{MUS}/m68kmake.exe", f"{MUS}/m68kmake.c"])
        subprocess.run([str(HERE / MUS / "m68kmake.exe")], cwd=HERE / MUS, check=True)
    sources = [str(args.probe.resolve()) if args.probe else "src/moon.c", "src/loader.c",
               f"{MUS}/m68kcpu.c", f"{MUS}/m68kops.c", f"{MUS}/softfloat/softfloat.c"]
    if dev:
        sources.append(f"{MUS}/m68kdasm.c")
    flags = ["-O2", "-std=c11", f"-DMOON_DEVELOPER={int(dev)}",
             f"-I{MUS}", f"-I{MUS}/softfloat", "-Isrc", f"-I{SDL}/include",
             "-Wno-unused-parameter", "-Wno-unused-but-set-variable", "-Wno-unused-function",
             "-Wno-date-time"]
    if args.typecheck:
        # Zig 0.16's driver does not support -fsyntax-only on this host. Compile
        # isolated objects instead, checking real types without linking/running.
        checkdir = HERE / "build/typecheck" / args.profile
        checkdir.mkdir(parents=True, exist_ok=True)
        for index, source in enumerate(sources):
            run(["cc", *flags, "-c", source, "-o", checkdir / f"source-{index}.obj"])
        for multi in (0, 1):
            run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", f"-DMOON_MULTIPLAYER={multi}",
                 "-c", "src/save_launcher.c", "-o", checkdir / f"launcher-{multi}.obj"])
        print(f"C typecheck passed ({args.profile})")
        return
    run(["rc", "app.rc", "app.res"], HERE / "icon")
    run(["cc", *flags, "-g" if dev else "-s", "-Wl,--subsystem,windows", *sources,
         f"{SDL}/lib/libSDL2.dll.a", "icon/app.res", "-o", out / f"{args.target}.exe"])
    if not dev:
        normalize_file(out / f"{args.target}.exe")
        store_icons(out / f"{args.target}.exe")
    shutil.copy2(HERE / SDL / "bin/SDL2.dll", out / "SDL2.dll")
    if args.probe:
        print(f"Built TEST ONLY: {out / (args.target + '.exe')}")
        return
    # These unchanged components keep their independent version/linker identity.
    # Rebuild from source and verify the exact tested hashes in both profiles.
    for multi, profile in enumerate(("Singleplayer", "Multiplayer")):
        resource = f"build/launcher-{profile}.res"
        run(["rc", "-d", f"MOON_MULTIPLAYER={multi}", "icon/launcher.rc", resource])
        run(["cc", "-Os", "-s", "-std=c11", "-nostdlib", "-Wl,--subsystem,windows",
             "-Wl,--entry,launcher_start", "-isystem",
             "./tools/zig-x86_64-windows-0.16.0/lib/libc/include/any-windows-any",
             f"-DMOON_MULTIPLAYER={multi}", "src/save_launcher.c", "icon/app.res", resource,
             "-lkernel32", "-luser32", "-o", out / f"Moonstone {profile}.exe"])
        inspect_pe(out / f"Moonstone {profile}.exe", stable_launcher=True)
    if not dev and args.target == "moonstone":
        record = {"schema": 1, "profile": "release", "inputs": input_hashes(),
                  "artifacts": {name: sha256(out / name) for name in ARTIFACTS}}
        manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        validate_build(out)
    print(f"Built {args.profile}: {out / (args.target + '.exe')}")


if __name__ == "__main__":
    main()
