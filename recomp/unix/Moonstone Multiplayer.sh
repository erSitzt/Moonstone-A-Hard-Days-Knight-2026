#!/bin/sh
# Starts Moonstone with the Multiplayer save folder (saves/Multiplayer).
cd "$(dirname "$0")" || exit 1
exec ./moonstone --save-profile multiplayer "$@"
