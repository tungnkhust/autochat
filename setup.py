from setuptools import find_packages, setup

VERSION: dict[str, str] = {}
with open("autochat/__version__.py") as version_file:
    exec(version_file.read(), VERSION)

with open("requirements.txt") as f:
    required_packages = f.readlines()

setup(
    name="autochat",
    version=VERSION["__version__"],
    packages=find_packages(),
    include_package_data=True,
    py_modules=["autochat"],
    install_requires=required_packages,
    python_requires=">=3.11",
    url="https://github.com/tungnkhust/autochat",
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    license="Apache 2.0",
)
