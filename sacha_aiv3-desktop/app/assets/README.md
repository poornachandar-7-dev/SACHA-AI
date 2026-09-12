# app/assets

Binary assets that are generated or provided during packaging:

- `icons/sacha.ico` — Windows app icon (build step: `scripts/build.py`)
- `icons/tray.png`  — system-tray icon
- `sounds/wake.wav` — wake-word chime
- `sounds/reply_chime.wav` — reply notification chime

Generate chimes with any editor or ship royalty-free samples here during
packaging. The directory is kept in git (empty) so the paths exist at build
time.