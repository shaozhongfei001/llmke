import os
import fnmatch
from setuptools import setup
from distutils.extension import Extension
from distutils.command.clean import clean
from Cython.Distutils import build_ext


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
                out.append(p)
    return out


def get_packages(root):
    out = []
    for (p, is_dir) in load_all(root):
        if is_dir:
            out.append(p)
    return out


# ex_files参数可以支持不在src文件夹下的文件进行加密
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


# 对加密后的py，pyc和c文件进行清除
class CleanCode(object):
    exclude_files = [
        "__init__.py",  # 保留包结构
        "fulltext_es_api_start.py",
        "graph_api_start.py",
        "structure_mysql_api_start.py",
        "vector_milvus_api_start.py",
        "gunicorn_conf.py"
    ]

    def clean_build(self, distribution):
        clean_command = clean(distribution)
        clean_command.all = True
        clean_command.finalize_options()
        clean_command.run()

    def delete(self, root, exts):
        src_files = load_files(root, exts=exts)
        for source_file in src_files:
            # 如果匹配免删除名单则跳过
            if any(fnmatch.fnmatch(source_file, pattern) or
                   fnmatch.fnmatch(os.path.basename(source_file), pattern)
                   for pattern in self.exclude_files):
                print(f"跳过文件: {source_file}")
                continue

            try:
                os.remove(source_file)
                print(f"已删除文件: {source_file}")
            except Exception as e:
                print(f"删除失败: {source_file}, 错误: {e}")

    def clean_pro(self, root):
        self.delete(root, exts=("pyd", "pyc", "c", "so"))

    def delete_source_code(self, root):
        self.delete(root, exts=("py", "c"))


for name in ["index_fulltext_service", "index_graph_service", "index_structure_service", "index_vector_service"]:
    MODULE_NAME = name  # 给项目名字
    root = name


    # 继承Cython的build_ext类
    class CustomBuildExt(build_ext, CleanCode):

        def run(self):
            self.clean_pro(root)
            build_ext.run(self)
            # self.clean_build(self.distribution)
            self.delete_source_code(root)  # 清理源代码，只保留编译后文件


    setup(
        name=MODULE_NAME,
        packages=get_packages(root),
        ext_modules=get_extensions(root),
        cmdclass={'build_ext': CustomBuildExt}  # 自定义的CustomBuildExt
    )
