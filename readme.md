# dexc

This Python project is an exception formatter that produces readable stack traces.

It only supports Python 3.12 and later.


## Features

### Current features

- Context displayed in addition to the trace line of each frame
- Reversed frame order i.e. JavaScript-like
- Truncated trace lines when there are too many
- Colorized stack trace obeying the the [NO_COLOR](https://no-color.org/) environment variable
- Minimzed frames when those are not part of the user code
- Support for exception groups
- Highlighting of re-raises i.e. when an exception is caught and re-raised with more than a simple `raise`, causing two stack traces to be concatenated without separation
- Formatting of [unraisable exceptions](https://docs.python.org/3/library/sys.html#sys.unraisablehook) e.g. raised in a destructor
- Support for syntax errors

### Future features

- Better checks e.g. when the column number is not available but the line number is
- Improve support for exception groups
- User vs lib tb kinds
- Avoid repeating recursive calls e.g. infinite loop
- Maximum screen width
- Option to reverse order
- Better highlight re-raises
- More ast nodes supported
- More precise ast node targeting e.g. should work if all statements are on the same line
- Handle multiprocessing.pool.RemoteTraceback which currently is text
- Better highlighting using ast data (e.g. only highlight first line of for loop)
- Formatting of exceptions raised in threads
- Better handling of file paths e.g. site-packages
- Perhaps syntax highlighting
- Avoid highlighting large nodes e.g. highlight a function and parentheses instead of the arguments if the function call is failing
- Other [escape codes](https://iterm2.com/documentation-escape-codes.html) e.g. curly underlines or clickable file names
- Other [characters](https://www.willmcgugan.com/blog/tech/post/ceo-just-wants-to-draw-boxes/)


## Installation

```sh
$ pip install dexc
```


## Usage

```py
import dexc
dexc.install()
```


## Prior art

- [Pretty traceback](https://github.com/mbarkhau/pretty-traceback)
- [Rich](https://www.willmcgugan.com/blog/tech/post/better-python-tracebacks-with-rich/)
- [Stack printer](https://github.com/cknd/stackprinter)
