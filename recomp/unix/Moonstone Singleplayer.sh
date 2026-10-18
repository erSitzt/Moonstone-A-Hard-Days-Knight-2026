#!/bin/sh
# Starts Moonstone with the Singleplayer save folder (saves/Singleplayer).
cd "$(dirname "$0")" || exit 1
exec ./moonstone --save-profile singleplayer "$@"
