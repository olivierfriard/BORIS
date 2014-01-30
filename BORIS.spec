# -*- mode: python -*-
a = Analysis(['boris.py'],
             pathex=['/Users/bene/work/boris/BORIS'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='boris',
          debug=True,
          strip=None,
          upx=False,
          console=False , icon='BORIS-logo.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               [('logo_boris_500px.png', 'logo_boris_500px.png', 'DATA')],
               [('dbios_unito.png', 'dbios_unito.png', 'DATA')],
               strip=None,
               upx=False,
               name='boris')
app = BUNDLE(coll,
             name='BORIS.app',
             icon='BORIS-logo.icns')
