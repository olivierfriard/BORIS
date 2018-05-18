# check if library in same dir than vlc.py
import pathlib
import sys
import ctypes

def find_local_lib():
    
    dll = None
    plugin_path = ""
    
    if sys.platform.startswith("linux"):
        return dll, plugin_path

    p = pathlib.Path(sys.argv[0])
    print("p", p)
    parent_dir = p.resolve().parent
    print("parent_dir", parent_dir)

    if sys.platform.startswith('win'):
        libname = 'libvlc.dll'
        
        lib_path = parent_dir / libname
        if lib_path.exists():
            dll = ctypes.CDLL(str(lib_path))
            plugin_path = str(parent_dir)

    if sys.platform.startswith("darwin"):

        libvlccore_path = parent_dir / "VLC" / "lib" / "libvlccore.dylib"
        libvlc_path = parent_dir / "VLC" / "lib" / "libvlc.dylib"

        if libvlccore_path.exists():
            ctypes.CDLL(str(libvlccore_path))
        if libvlc_path.exists():
            dll = ctypes.CDLL(str(libvlc_path))

        plugin_path = parent_dir / "VLC" / "plugins"
        if plugin_path.exists():
            plugin_path = str(plugin_path)

    return dll, plugin_path


if __name__ == '__main__':
    print(find_local_lib)
