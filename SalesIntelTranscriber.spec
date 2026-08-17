# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\sales_transcriber\\web_ui.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src\\sales_transcriber\\web_static', 'sales_transcriber\\web_static'), ('.venv\\Lib\\site-packages\\faster_whisper\\assets', 'faster_whisper\\assets')],
    hiddenimports=[],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pyannote', 'speechbrain', 'torch', 'torchaudio', 'torchvision', 'tensorflow', 'matplotlib', 'pandas', 'scipy', 'sklearn'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SalesIntelTranscriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SalesIntelTranscriber',
)
