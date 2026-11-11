# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project = Path(SPECPATH).parent
assets = project / "src" / "convertly" / "ui" / "assets"

datas = [
    (str(assets), "convertly/ui/assets"),
    (str(project / "LICENSE"), "."),
    (str(project / "THIRD_PARTY_NOTICES.md"), "."),
]

binaries = []
for name in ("ffmpeg", "ffprobe"):
    for suffix in ("", ".exe"):
        candidate = project / "vendor" / f"{name}{suffix}"
        if candidate.exists():
            binaries.append((str(candidate), "bin"))

a = Analysis(
    [str(project / "packaging" / "entry.py")],
    pathex=[str(project / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Convertly",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project / "packaging" / "convertly.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Convertly",
)
