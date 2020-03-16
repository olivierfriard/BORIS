# https://stackoverflow.com/questions/44977227/how-to-configure-main-py-init-py-and-setup-py-for-a-basic-package

from setuptools import setup

setup(
   name='boris-behav-obsr',
   version=[x for x in open("boris/version.py","r").read().split("\n") if "__version__" in x][0].split(" = ")[1].replace('"', ''),
   description='BORIS',
   author='Olivier Friard - Marco Gamba',
   author_email='olivier.friard@unito.it',
   long_description=open("README_pip.rst", "r").read(),
   #long_description_content_type="text/markdown",
   url="http://www.boris.unito.it",
   python_requires=">=3.6",
   classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        "Operating System :: OS Independent",
    ],
    packages=['boris'],  #same as name
   
    install_requires=[
          "matplotlib",
          "numpy",
          "tablib",
          "python-intervals",
          "pyqt5"
      ],

    include_package_data=True,

    # package_data={
    # 'behatrix': ['behatrix.qrc', 'behatrix.ui', 'LICENSE.TXT', 'README.TXT'],
    # },

    entry_points={
        'console_scripts': [
            'boris = boris:main',
        ],
    }
 )
