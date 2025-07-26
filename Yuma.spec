# -*- mode: python ; coding: utf-8 -*-

# Adicionamos estas importações para encontrar os arquivos necessários automaticamente
from pathlib import Path
import customtkinter

block_cipher = None

a = Analysis(
    ['testeia.py'],  # <<< CORRIGIDO: Apenas o seu script principal aqui.
    pathex=[],
    binaries=[],
    # <<< ADICIONADO: Inclui a pasta de assets do customtkinter.
    datas=[(str(Path(customtkinter.__file__).parent), 'customtkinter/')],
    # <<< ADICIONADO: Informa ao PyInstaller sobre módulos que ele não acha sozinho.
    hiddenimports=['google.api_core.bidi', 'google.api_core.client_options', 'google.auth.transport.grpc'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    # optimize=0 foi removido para usar o padrão, não é necessário.
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Yuma',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # <<< Perfeito, mantém a janela preta oculta.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # <<< CORRIGIDO: Aponta para o arquivo .ico relativo ao projeto.
    icon='icone.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Yuma',
)