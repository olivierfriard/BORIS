# -*- mode: python -*-
a = Analysis(['boris.py'],
             pathex=['c:\\Users\\User\\projects\\boris\\master'],
             hiddenimports=['sip'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='boris.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               [('logo_boris_500px.png', 'logo_boris_500px.png', 'DATA')],
               [('dbios_unito.png', 'dbios_unito.png', 'DATA')],
               [('splash.png', 'splash.png', 'DATA')],
               strip=None,
               upx=False,
               name='boris')
