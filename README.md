Free-Wili Firmware Updater
==========================

Firmware Updater for Free-Wili devices.


Development
===========

```bash
$ uv venv
$ source .venv/bin/activate
$ uv sync
$ pyside6-uic ./src/ui/main.ui -o ./src/ui/main.py --from-imports .
$ pyside6-rcc ./src/ui/main.qrc -o ./src/ui/main_rc.py
$ uv run python main.py
```

```bash
$ pyinstaller main.spec
```


License
=======

MIT
