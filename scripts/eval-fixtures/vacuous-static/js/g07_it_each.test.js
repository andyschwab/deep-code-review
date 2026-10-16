const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test.each([[9, 3], [-9, 0], [2, 2]])('clamp(%i)', (x, want) => {
  expect(clamp(x, 0, 3)).toBe(want);
});
