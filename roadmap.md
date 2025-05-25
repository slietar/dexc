# Roadmap

- [x] Better checks e.g. when the column number is not available but the line number is
- [x] Improve support for exception groups
- [x] User vs lib tb kinds
- [x] Avoid repeating recursive calls e.g. infinite loop
- [x] Maximum screen width
- [x] Option to reverse order
- [-] Better highlight re-raises
- [x] More ast nodes supported
- [x] More precise ast node targeting e.g. should work if all statements are on the same line
- [-] Handle multiprocessing.pool.RemoteTraceback which currently is text
- [-] Better highlighting using ast data (e.g. only highlight first line of for loop)
- [-] Formatting of exceptions raised in threads and processes, use `threading.excepthook`
- [x] Better handling of file paths e.g. site-packages
- [-] Perhaps syntax highlighting
- [-] Avoid highlighting large nodes e.g. highlight a function and parentheses instead of the arguments if the function call is failing
- [-] Other [escape codes](https://iterm2.com/documentation-escape-codes.html) e.g. curly underlines or clickable file names
- [-] Other [characters](https://www.willmcgugan.com/blog/tech/post/ceo-just-wants-to-draw-boxes/)
- [-] Smaller traces when explicit raise
- [-] Adapt to window height
- [x] Bug when `[Caused by]` is inside exception groups
- [-] Show a single listing when the same file is in multiple frames
- [-] Show function and class definitions from earlier
- [x] Support for IPython e.g. by calling `IPython.get_ipython().set_custom_exc(...)` and ensuring there is still color there; metadata on which cell the exception was raised in
  - [x] https://github.com/ipython/ipython/blob/main/IPython/core/ultratb.py
  - [x] https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.ultratb.html
- [-] When printing `[Raised while handling]` or `[Caused by]`, merge both traces at the try/except statement
- [-] When too many lines, show at least the first and last lines of the relevant statement
- [x] Protect against too many columns
  - [x] Frame header
  - [x] Frame code listing
- [x] Exception info serialization
- [x] Remove newline when highlight is on last line e.g.
  ```
      4 raise Exception
        ^^^^^^^^^^^^^^^
                                     <--- Remove this line
  at _run_code (<frozen runpy>)
  at _run_module_as_main (<frozen runpy>)
  ```
- [-] Remove empty code line when line above is highlight
- [x] Add env variable to disable hook
- [x] Only import on hook call
- [-] Use grapheme clusters for measuring width
- [-] Unicode file paths
- [x] Formatting of warnings by overriding `warnings.showwarning`
- [x] Better indentation
- [ ] Check on Google Colab
- [-] Remove path of files in temporary directory
- [ ] Add option to only handle certain exception types
- [x] Optimize compression algorithm
- [x] Use best compression algorithm solution when multiple solutions with the same cost exist
- [ ] Integration with the `logging` module
- [x] Show correct number of frames
- [x] Bug in exception groups: first child seems to have less indentation (see screenshot)
- [x] Restore syntax errors
- [x] Compiled code
- [x] Import failures
- [x] Exception notes (PEP 678)
- [x] Print less whitespace
- [x] Remove final newline
- [ ] Configuration versioning
- [-] When printing a RecursionError, do not display any traces
- [-] Merge warnings
- [ ] Remove duplicates in exception groups
- [ ] Remove frames common between exceptions in exception groups
- [ ] Test on other platforms
  - [ ] Windows
  - [ ] Linux
- [ ] Test on workspaces e.g. detect editable installs
- [x] Fill to return exactly `width` characters in order to draw boxes
- [x] Support for `__tracebackhide__`
- [x] For simplicity, JAX has removed its internal frames from the traceback of the following exception. Set JAX_TRACEBACK_FILTERING=off to include these.
  - [x] Also `HYDRA_FULL_ERROR=1`
- [x] In error messages with URLs, make the URLs clickable ~~and shorten long URLs~~
- [ ] Fix repeat box inset
- [x] Remove final newline
- [ ] Don't display chains of module-level imports
- [ ] If there was no `raise` at the start, show it even if it's a library
- [ ] Remove pre context if is has higher indentation than target, and post context if it has a much lower indentation than target
- [x] Use terminal width with a minimum and maximum
- [x] Remove duplicate utility function
- [ ] Environment variable to add detail
- [x] Link line number and column number
- [-] Alternative to `^^^^` for highlighting
- [x] Fix `at <module>` (e.g. t32)
- [x] Fix split URLs
- [ ] More URLs in notes, single-line descriptions, etc.
- [x] Test long descriptions and notes within exception groups, with a box
- [x] Optional module name in left title of frames
- [x] Choose generic indent width
- [x] Fix link option
- [x] Remove line of `-` in notes
- [-] Remove trailing whitespace when unncessary
- [x] Fix incorrect line width
- [x] Wrap into ellipsis: right-strip before adding ellipsis
- [ ] Check wrapping of whitespace
- [ ] Skip lib frames when explicit raise that comes from same root module
  - [ ] Also handle re-raises and excepts intelligently
- [x] Remove/move utility functions from `render.py`
- [x] Move first line of description back to first printed line e.g. polars the truth value of a Series is ambiguous
- [x] Remove URLs on Jupyter notebooks, i.e. when there is no `$TERM_PROGRAM` (see screenshot and https://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html#IPython.display.FileLink)
- [-] Different themes
- [x] Improve handling of:
  - [-] ImportError (see screenshot)
  - [x] SyntaxError (see screenshot)
- [-] Autoreloaded files show up as `<string>` (see screenshot and https://github.com/ipython/ipython/blob/90414abb5203a34e3e35225b4897db7720f8ed98/IPython/extensions/autoreload.py)
- [ ] Show trace at each module frontier
- [ ] Rewrite "Raised while handling" to be more clear
- [x] Support `FORCE_COLOR` environment variable
- [-] Full HTML output in Jupyter notebooks using `display(HTML(...))`
- [x] Improve syntax error source
- [x] Ellipsis in warnings bug
- [ ] Errors in `unittest` and `pytest`
- [-] Put keywords in bold
- [ ] Put long highlights vertically
- [ ] Concatenate "in module" -> test on matplotlib >20 figures
- [ ] Support other output types such as GH Actions (see screenshot)
- [ ] Fold when it's just a function call of an argument
- [ ] Inset of repeat box not working
- [ ] Check behavior when there are no frames
- [ ] Logging errors (see https://docs.python.org/3/library/logging.html#logging.Handler.handleError)
- [x] Problem when current project is installed
- [-] t35 completed missing (see screenshot)
- [x] Order seems swapped in warnings
- [x] t20 wrong path -> remove import detection
- [x] Set environment variables for libraries: Jax and Hydra
- [ ] More space after line numbers
- [ ] When considering highlighting lines (and not particular columns), check if
  there could be an ambiguity with a parent expression that is on the same lines
- [ ] Ensure same ordering as native Python

Manipulating locals: see PEP 667
Cool error reporting: https://lib.rs/crates/ariadne

Grapheme clustering + shaper clustering
  https://github.com/wezterm/wezterm/issues/4320
  https://github.com/jquast/wcwidth/tree/master
  https://mitchellh.com/writing/grapheme-clusters-in-terminals
  https://gist.github.com/andjc/43a98c6d6f5e419303604081d57a401e
