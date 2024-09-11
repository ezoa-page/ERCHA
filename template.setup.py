from setuptools import setup, find_packages
from setuptools.extension import Extension

setup(
    name="{{namelc}}",
    version="{{version}}",
    packages=find_packages(),  # Automatically find and include all Python packages
    include_package_data=True, # Include other files listed in MANIFEST.in (if any)
    entry_points={
        'console_scripts': [
            'ercha=ercha.cli:main',
        ],
    },
    author="{{author}}",
    author_email="{{author_email}}",
    description="{{description}}",
    url="{{url}}",
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
