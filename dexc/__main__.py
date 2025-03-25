import json
from dataclasses import asdict

from .options import OPTIONS_ABSOLUTE_PATH, OPTIONS_RELATIVE_PATH, Options


if OPTIONS_ABSOLUTE_PATH.exists():
  with OPTIONS_ABSOLUTE_PATH.open() as options_file:
    options_dict = json.load(options_file)

  Options(**options_dict)

  print(f'Reading options from ~/{OPTIONS_RELATIVE_PATH}')
else:
  options = Options()
  options_dict = asdict(options)

  OPTIONS_ABSOLUTE_PATH.parent.mkdir(exist_ok=True, parents=True)

  with OPTIONS_ABSOLUTE_PATH.open('w') as options_file:
    json.dump(options_dict, options_file, indent=4)

  print(f'Writing options to ~/{OPTIONS_RELATIVE_PATH}')

print('\nOptions:')

for key, value in options_dict.items():
  print(f'  {key} = {value!r}')
