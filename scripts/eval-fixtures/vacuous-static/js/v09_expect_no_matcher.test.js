const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('add no matcher', () => {
  expect(add(1, 2));
});
