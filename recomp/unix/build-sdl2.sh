#!/bin/sh
# Builds the SDL2 shared library that the macOS/Linux packages bundle next to
# the moonstone binary (same SDL version as the Windows release, see
# THIRD-PARTY-NOTICES.txt). Installs into recomp/vendor/SDL2-unix, which
# build.py prefers over a system SDL2.
#
# Distribution packages are not bundled: Homebrew's sdl2 is sdl2-compat (needs
# SDL3 at runtime) and Debian/Ubuntu's libSDL2 links X11, PulseAudio, Wayland
# and more directly. This build loads those back ends with dlopen at runtime,
# so the library itself only needs libc (Linux) or system frameworks (macOS).
# Linux: install the X11/Wayland/ALSA/PulseAudio -dev headers first, otherwise
# configure leaves those back ends out (see .github/workflows/unix-release.yml).
set -eu
VERSION=2.32.10
SHA256=5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165
RECOMP=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$RECOMP/vendor/SDL2-unix"
WORK="$RECOMP/build/sdl2-src"
TARBALL="$WORK/SDL2-$VERSION.tar.gz"

mkdir -p "$WORK"
if [ ! -f "$TARBALL" ]; then
    curl -fsSL -o "$TARBALL.part" \
        "https://github.com/libsdl-org/SDL/releases/download/release-$VERSION/SDL2-$VERSION.tar.gz"
    mv "$TARBALL.part" "$TARBALL"
fi
if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$TARBALL" | cut -d' ' -f1)
else
    actual=$(shasum -a 256 "$TARBALL" | cut -d' ' -f1)
fi
if [ "$actual" != "$SHA256" ]; then
    echo "SDL2 tarball checksum mismatch: $actual" >&2
    rm -f "$TARBALL"
    exit 1
fi

rm -rf "$WORK/SDL2-$VERSION" "$PREFIX"
tar -xzf "$TARBALL" -C "$WORK"
cd "$WORK/SDL2-$VERSION"
./configure --prefix="$PREFIX" --disable-static --disable-rpath
jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)
make -j"$jobs"
make install
echo "SDL2 $VERSION installed in $PREFIX"
