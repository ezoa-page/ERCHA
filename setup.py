from setuptools import setup, find_packages
from setuptools.extension import Extension

setup(
    name="ercha",
    version="0.1.1",
    packages=find_packages(),  # Automatically find and include all Python packages
    include_package_data=True, # Include other files listed in MANIFEST.in (if any)
    entry_points={
        'console_scripts': [
            'ercha=ercha.cli:main',
        ],
    },
    author="Ezoa",
    author_email="rawr@ezoa.page",
    description="Ezoa's Resource Content Handler Archiver - A Furcadia RCH file archive tool",
    url="https://eoza.page/projects/ERCHA/",
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
