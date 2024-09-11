# ERCHA Development README

## Windows dependencies
### First, run CMD as administrator
```cmd
winget install -e --id=Python.Python.3.12
winget install -e --id=WiXToolset.WiXCLI
```
### Second, run cmd as regular user
```
pip install setuptools pyinstaller Cython
```

## Running ERCHA from sources
```bash
python -m ercha.cli
```

## Running unit tests
ERCHA comes with some basic unit tests for validating functionality.

### Run all tests
```bash
python -m unittest discover -s tests
```

### Run individual unit test files
```bash
python -m unittest discover -s tests -p test_functional.py
python -m unittest discover -s tests -p test_security.py
python -m unittest discover -s tests -p test_additional.py
```

## Generating configuration files for version release, i.e. 0.1.0
```bash
python generate_configuration.py 0.1.0
```

## Building for Linux

```bash
python -m build
```

### Uploading to PyPI

```bash
python3 -m twine upload --repository pypi dist/*
```

## Building for Windows

### Run executable build script
Run `build_exe.cmd`, this will build the executable using pyinstaller. There is a small wrapper script `ercha_launcher.py` used to launch the cli code. Installer will also be built.
This also generates the appropriate winget manifests in the `winget` path.

### Uploading to Winget
* Create release on Github using version number as tag.
* Include MSI in release.
* Copy the version folder i.e `0.1.0` from inside the `winget` path to `https://github.com/ezoa-page/fork-winget-pkgs/tree/master/manifests/e/Ezoa/ERCHA/`, then do a pull request.
