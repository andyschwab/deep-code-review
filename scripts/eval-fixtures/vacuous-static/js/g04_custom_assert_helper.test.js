const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

function assertSquares(xs) {
  expect(xs[0]).toBe(0);
  expect(xs).toEqual([...xs].sort((a, b) => a - b));
}

test('squares sorted', () => {
  assertSquares(squares(5));
});
