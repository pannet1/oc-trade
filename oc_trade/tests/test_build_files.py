from toolkit.fileutils import Fileutils

f = Fileutils()
BUILD_PATH = "strikes/"
lst_build_files = f.get_files_with_extn('yaml', BUILD_PATH)

print(lst_build_files)
