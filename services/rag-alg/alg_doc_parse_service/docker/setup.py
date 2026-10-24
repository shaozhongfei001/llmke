import os
from setuptools import setup
from distutils.extension import Extension
from distutils.command.clean import clean
from Cython.Distutils import build_ext

# 要跳过打包和删除的文件名或路径
SKIP_FILES = [
    "__init__.py",
    "server/controller.py",
    "server/api_param.py",
    "server/response_model.py",
    "server/data_access_object.py",
    "server/process_reporter.py",
    "server/nacos_utils.py"
]

def load_all(root):
    out = []
    if os.path.isdir(root):
        out.append((root, True))
        names = os.listdir(root)
        for name in names:
            p = os.path.join(root, name)
            if os.path.isdir(p):
                out += load_all(p)
            else:
                out.append((p, False))
    else:
        out.append((root, False))
    return out

def load_files(root, exts=("py",)):
    out = []
    for (p, is_dir) in load_all(root):
        if not is_dir:
            ext = p.split(".")
            if len(ext) > 1 and ext[-1] in exts:
                # 检查是否在忽略列表
                rel_path = os.path.relpath(p, start=os.getcwd())
                filename = os.path.basename(p)
                if any(skip in [filename, rel_path] for skip in SKIP_FILES):
                    continue
                out.append(p)
    return out

def get_packages(root):
    out = []
    for (p, is_dir) in load_all(root):
        if is_dir:
            out.append(p)
    return out

def get_extensions(root):
    py_files = load_files(root, exts=("py",))
    ext_names = map(lambda x: x.replace(os.path.sep, '.')[:-3], py_files)

    def make_extension(ext_name):
        ext_path = ext_name.replace('.', os.path.sep) + '.py'
        ext = Extension(ext_name, [ext_path], include_dirs=['.'])
        ext.cython_directives = {'language_level': "3"}
        return ext

    extensions = map(lambda x: make_extension(x), ext_names)
    return list(extensions)

class CleanCode(object):

    def clean_build(self, distribution):
        clean_command = clean(distribution)
        clean_command.all = True
        clean_command.finalize_options()
        clean_command.run()

    def delete(self, root, exts):
        src_files = load_files(root, exts=exts)
        for source_file in src_files:
            # 删除时也跳过 SKIP_FILES
            rel_path = os.path.relpath(source_file, start=os.getcwd())
            filename = os.path.basename(source_file)
            if any(skip in [filename, rel_path] for skip in SKIP_FILES):
                continue
            if os.path.exists(source_file):
                os.remove(source_file)

    def clean_pro(self, root):
        self.delete(root, exts=("pyd", "pyc", "c", "so"))

    def delete_source_code(self, root):
        self.delete(root, exts=("py", "c"))


for name in ["server", "deepdoc"]:
    MODULE_NAME = name
    root = name

    class CustomBuildExt(build_ext, CleanCode):
        def run(self):
            self.clean_pro(root)
            build_ext.run(self)
            self.delete_source_code(root)  # 清理源代码，只保留编译后文件

    setup(
        name=MODULE_NAME,
        packages=get_packages(root),
        ext_modules=get_extensions(root),
        cmdclass={'build_ext': CustomBuildExt}
    )
