const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('add values', () => {
  expect(add(2, 3)).toBe(5);
  expect(add(-1, 1)).toBe(0);
});
