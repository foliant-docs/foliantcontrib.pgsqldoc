from shutil import copyfile
from pathlib import PosixPath


def copy_if_not_exists(source: PosixPath,
                       to_copy: PosixPath):
    '''if source file does not exist — copy to_copy file on its place.

    source (PosixPath) — path to source file
    to_copy (PosixPath) - path to the file to be copied
    '''
    if source.exists():
        return
    else:
        copyfile(to_copy, source)
