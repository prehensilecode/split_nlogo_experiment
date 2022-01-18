# split_nlogo_experiment Installation Instructions

This package is not currently available on [PyPI](https://pypi.org).

## Build and Install
This package assumes use of Python 3. It has been tested with
Python >= 3.6.

### Prerequisites
Install these packages with `pip`
- build

### Build
To build:
```
$ tar -xf split_nlogo_experiment-v0.XXX.tar.gz
$ cd split_nlogo_experiment-v0.XXX
$ python -m build
```

### Install
If the build was successful, i.e. there were no error messages, 
a `wheel` (`.whl`) file will be produced in the `dist` 
directory. Install that wheel:
```
$ cd dist
$ pip install --user split_nlogo_experiment-0.XXX-py3-none-any.whl
```
where `XXX` should be replaced with the actual version number
in the `.whl` file name.

### Modify PATH if necessary
`pip install --user` will install in a user-specific private
directory. This location varies by platform.

On macOS, it is usually:
```
    ~/Library/Python/3.X/bin
```
where `X` is replaced with the minor version of the Python 
you have installed (whether Apple-provided, via Homebrew,
via Anaconda, or something else).

On Linux, it is usually:
```
    ~/.local/bin
```

In any case, you may need to modify your login file to add
the appropritate directory to your `PATH` environment variable.
That file depends on your shell.

For macOS, which now defaults to ZSH, the file is `~/.zshrc`. 
For Linux, it is typically Bash, and the file is `~/.bashrc`.

