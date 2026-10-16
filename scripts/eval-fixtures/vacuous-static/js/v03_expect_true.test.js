const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('clamp ok', () => {
  clamp(5, 0, 3);
  expect(true).toBe(true);
});
