def main():
  raise ExceptionGroup('group', [
    ExceptionGroup('inner group', [
      Exception('bar'),
    ]),
    Exception('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus vitae mi quam. Sed aliquet enim ac blandit rhoncus. In venenatis tellus arcu, at efficitur nisi tristique sed. Ut scelerisque malesuada dui ac consectetur. Pellentesque leo purus, gravida id nunc eu, scelerisque convallis velit. Morbi massa erat, lobortis nec urna et, commodo feugiat nulla. Maecenas varius dolor vel urna accumsan, quis ultrices dui vulputate. Praesent elementum, tortor a feugiat porta, velit nisi auctor nisl, in iaculis tortor ante et odio. Aliquam ut vestibulum libero.'),
    Exception('baz'),
    Exception('qux'),
    Exception('quux'),
    Exception('corge'),
    Exception('grault'),
    Exception('garply'),
    Exception('waldo'),
    Exception('fred'),
    Exception('plugh'),
    Exception('xyzzy'),
    Exception('thud'),
  ])
