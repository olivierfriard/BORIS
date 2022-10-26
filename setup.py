# https://stackoverflow.com/questions/44977227/how-to-configure-main-py-init-py-and-setup-py-for-a-basic-package

from setuptools import setup

setup(
    name="boris-behav-obs",
    version=[x for x in open("boris/version.py", "r").read().split("\n") if "__version__" in x][0]
    .split(" = ")[1]
    .replace('"', ""),
    description="BORIS - Behavioral Observation Research Interactive Software",
    author="Olivier Friard - Marco Gamba",
    author_email="olivier.friard@unito.it",
    long_description=open("README.rst", "r").read(),
    long_description_content_type="text/x-rst",
    # long_description_content_type="text/markdown",
    url="http://www.boris.unito.it",
    project_urls={
        "Documentation": "https://boris.readthedocs.io/en/latest/",
        "Changelog": "https://github.com/olivierfriard/BORIS/wiki/BORIS-change-log-v.8",
        "Source code": "https://github.com/olivierfriard/BORIS",
        "Issues": "https://github.com/olivierfriard/BORIS/issues",
    },
    python_requires=">=3.6",
    classifiers=[
        "Topic :: Scientific/Engineering",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    packages=["boris"],  # same as name
    install_requires=[
        "exifread>=3.0.0",
        "pillow>=9.1.1",
        "numpy>=1.21",
        "matplotlib>=3.3.3",
        "pandas>=1.3.5",
        "tablib[html, ods, xls, xlsx, pandas, cli]>=3",
        "pyqt5>=5.15",
        "pyreadr",
    ],
    package_data={
        "boris": [
            "core.qrc",
            "core.ui",
            "add_modifier.ui",
            "converters.ui",
            "edit_event.ui",
            "observation.ui",
            "param_panel.ui",
            "preferences.ui",
            "project.ui",
            "portion/*.py",
        ],
        "": ["README.TXT", "LICENSE.TXT"],
    },
    entry_points={
        "console_scripts": [
            "boris = boris:main",
        ],
    },
)
