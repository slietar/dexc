# dexc

Dexc is a Python exception formatter. It supports Python 3.13 and later.


## Features

- Context displayed in addition to the main line of each frame
- Truncated trace lines when there are too many
- Colorized stack trace obeying the the [NO_COLOR](https://no-color.org/) environment variable
- Minimization of frames when they are not part of the user code
- Support for Exception groups
- Highlighting of re-raises i.e. when an exception is caught and re-raised with more than a simple `raise`, causing two stack traces to be concatenated without separation
- Handling of [unraisable exceptions](https://docs.python.org/3/library/sys.html#sys.unraisablehook) e.g. raised in a destructor
- Support for syntax errors
- Support for exception notes
- Support for warnings
- Collapse of repeated frames or groups of frames
- Disabling using the `DEXC_DISABLE=1` environment variable


## Caveats

Dexc should not be used in production code or to format untrusted exceptions. Because it relies on certain CPython-specific APIs, it may break on other runtimes or if your code displays exotic behavior, such as modifying `sys.modules` or updating source files while the program is running.

Furthermore, Dexc may produce incorrect output if your code or exception messages contain non-ASCII characters.


## Installation

```sh
$ pip install dexc
```


## Usage

```py
import dexc
dexc.install()

# Or:

import dexc.autoinstall
```


## Related work

| Name                                                                                                | Local lookup | Notes                                                                                                   |
|-----------------------------------------------------------------------------------------------------|--------------|---------------------------------------------------------------------------------------------------------|
| [backtrace](https://github.com/nir0s/backtrace)                                                     | no           | One line per frame                                                                                      |
| [better-exceptions](https://github.com/qix-/better-exceptions)                                      | yes          | Same layout as the default                                                                              |
| [colored-traceback](https://github.com/staticshock/colored-traceback.py)                            | no           | Adds color to the default traceback                                                                     |
| [friendly-traceback](https://github.com/friendly-traceback/friendly-traceback)                      | no           | Provides error explanations                                                                             |
| [frosch](https://github.com/HallerPatrick/frosch)                                                   | yes          |                                                                                                         |
| [IPython ultratb](https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.ultratb.html) | no           | Same layout as the default                                                                              |
| [Pretty Traceback](https://github.com/mbarkhau/pretty-traceback)                                    | no           | One line per frame                                                                                      |
| [pretty-errors](https://github.com/onelivesleft/PrettyErrors)                                       | yes          |                                                                                                         |
| [ptb](https://github.com/chillaranand/ptb)                                                          | no           |                                                                                                         |
| [Rich tracebacks](https://rich.readthedocs.io/en/stable/traceback.html)                             | no           | See also [this article](https://www.willmcgugan.com/blog/tech/post/better-python-tracebacks-with-rich/) |
| [rich-traceback](https://github.com/laurb9/rich-traceback)                                          | no           |                                                                                                         |
| [stackprinter](https://github.com/cknd/stackprinter)                                                | yes          |                                                                                                         |
| [TBVaccine](https://github.com/skorokithakis/tbvaccine)                                             | yes          | Same layout as the default; includes `.pth`                                                             |
