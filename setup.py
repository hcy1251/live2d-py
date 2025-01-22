import os
import platform
import re
import subprocess
import sys
import shutil
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext

NAME = "live2d-py"
VERSION = "0.3.4"
DESCRIPTION = "Live2D Python SDK"
LONG_DESCRIPTION = open("README.md", "r", encoding="utf-8").read()
AUTHOR = "Arkueid"
AUTHOR_EMAIL = "thetardis@qq.com"
URL = "https://github.com/Arkueid/live2d-py"
REQUIRES_PYTHON = ">=3.2"
INSTALL_REQUIRES = ["numpy", "pyopengl", "pillow"]

def ensure_directories():
    dirs = ['package/live2d/v3']
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def copy_library_file(src_dir, dst_dir):
    # 對於 macOS，我們需要複製 .dylib 文件並重命名為 .so
    if platform.system() == "Darwin":
        dylib_path = os.path.join(src_dir, "lib", "Release", "libLAppModelWrapper.dylib")
        so_path = os.path.join(dst_dir, "live2d.so")
        if os.path.exists(dylib_path):
            shutil.copy2(dylib_path, so_path)
            return True
    return False

class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[], py_limited_api=True)
        self.sourcedir = os.path.abspath(sourcedir)

def is_virtualenv():
    return 'VIRTUAL_ENV' in os.environ

def get_base_python_path(venv_path):
    return re.search("home = (.*)\n", open(os.path.join(venv_path, "pyvenv.cfg"), 'r').read()).group(1)

class CMakeBuild(build_ext):
    def get_cmake_version(self):
        try:
            out = subprocess.check_output(["cmake", "--version"])
        except:
            sys.stderr.write("CMake must be installed to build the following extensions: " + ", ".join(str(self.extensions)))
            sys.exit(1)
        return re.search(r"cmake version ([0-9.]+)", out.decode()).group(1)

    def run(self):
        cmake_version = self.get_cmake_version()
        if platform.system() == "Windows":
            if cmake_version < "3.12":
                sys.stderr.write("CMake >= 3.12 is required")
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        ensure_directories()
        
        cmake_args = []
        build_args = ["--config", "Release"]

        if platform.system() == "Windows":
            if platform.python_compiler().find("64 bit") > 0:
                print("Building for 64 bit")
                cmake_args += ["-A", "x64"]
            else:
                print("Building for 32 bit")
                cmake_args += ["-A", "Win32"]
            build_args += ["--", "/m:2"]
        else:
            cmake_args += ["-DCMAKE_BUILD_TYPE=" + "Release"]
            if platform.system() == "Darwin":
                cmake_args += ["-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0"]
            build_args += ["--", "-j2"]
            
        build_folder = os.path.abspath(self.build_temp)

        if not os.path.exists(build_folder):
            os.makedirs(build_folder)

        if is_virtualenv():
            python_installation_path = get_base_python_path(os.environ["VIRTUAL_ENV"])
        else:
            python_installation_path = os.path.split(sys.executable)[0]
        print("Python installation path: " + python_installation_path)
        sys.stdout.flush()

        cmake_args += ["-DPYTHON_INSTALLATION_PATH=" + python_installation_path]

        cmake_setup = ["cmake", ext.sourcedir] + cmake_args
        cmake_build = ["cmake", "--build", "."] + build_args

        print("Building extension for Python {}".format(sys.version.split('\n', 1)[0]))
        print("Invoking CMake setup: '{}'".format(' '.join(cmake_setup)))
        sys.stdout.flush()
        subprocess.check_call(cmake_setup, cwd=build_folder)
        print("Invoking CMake build: '{}'".format(' '.join(cmake_build)))
        sys.stdout.flush()
        subprocess.check_call(cmake_build, cwd=build_folder)
        
        # 在構建完成後手動複製文件
        dst_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "package", "live2d", "v3")
        if not copy_library_file(build_folder, dst_dir):
            raise RuntimeError("Failed to copy library file")

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="MIT",
    url=URL,
    install_requires=INSTALL_REQUIRES,
    ext_modules=[CMakeExtension("LAppModelWrapper", ".")],
    cmdclass={"build_ext": CMakeBuild},
    packages=find_packages("package"),
    package_data={
        "live2d": [
            "v3/*.so",
            "v3/*.pyd",
            "v3/*.dylib",
        ]
    },
    package_dir={"": "package"},
    keywords=["Live2D", "Cubism Live2D", "Cubism SDK", "Cubism SDK for Python"],
    python_requires=REQUIRES_PYTHON
)