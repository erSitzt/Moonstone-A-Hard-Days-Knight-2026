================================================================
  MOONSTONE - A Hard Days Knight      native macOS / Linux port
================================================================

Moonstone 2026 v1.5. Same game, fixes and save format as the Windows
release. ADF files are not included.


---------------------------------------------------------------
 REQUIREMENTS
---------------------------------------------------------------

Nothing to install. SDL2 is included next to the game (macOS:
libSDL2-2.0.0.dylib, Linux: libSDL2-2.0.so.0); keep it in the folder.
Packages: macOS 11 or newer on Apple silicon (arm64); 64-bit Linux (x64)
with glibc 2.39 or newer (e.g. Ubuntu 24.04) and an X11 or Wayland desktop.

macOS: the game is not signed. If macOS refuses to open it, run this once
in Terminal, inside the extracted folder:

    xattr -dr com.apple.quarantine .


---------------------------------------------------------------
 HOW TO PLAY
---------------------------------------------------------------

1. Extract the complete archive.
2. Put your three ADF files into the data folder, named exactly:

       Disk1.adf
       Disk2.adf
       Disk3.adf

3. Start the game:

   macOS: double-click

       Moonstone Singleplayer.command   (uses saves/Singleplayer/singleplayer.sav)
   or  Moonstone Multiplayer.command   (uses saves/Multiplayer/multiplayer.sav)

   Linux: run from a terminal inside the folder (many file managers can also
   start them with a double-click, "Run as program"):

       ./"Moonstone Singleplayer.sh"
   or  ./"Moonstone Multiplayer.sh"

   Running ./moonstone directly uses the Singleplayer save folder.

On first launch the game extracts its boot modules from Disk1.adf. Each ADF
must be 901,120 bytes. Keep moonstone, the SDL2 library, the launch
scripts and the data folder together; the folder is portable. Saves from the Windows release are
compatible: copy them into the matching saves folder.


---------------------------------------------------------------
 CONTROLS
---------------------------------------------------------------

  Arrow keys / left stick ...... move / move the pointer
  Ctrl / Enter / A ............. attack / select / confirm
  Space or I / Y ............... open inventory on the map
  X / B ........................ close inventory
  Space / Start (in combat) .... pause / resume
  E / Back ..................... rest / end the current turn
  F5 / F9 ...................... quicksave / quickload
  F11 .......................... toggle fullscreen

All bindings and the multiplayer device rules are described in controls.ini
and in the project README:
https://github.com/Undine1/Moonstone-A-Hard-Days-Knight-2026

If the game does not start, check moonstone.log in this folder. It lists the
operating system, disk paths, sizes and any read/write errors.

MOONSTONE (c) 1991 Mindscape International / Rob Anderson.
Native runtime (c) 2026 Undine1, licensed under GPL v3.
