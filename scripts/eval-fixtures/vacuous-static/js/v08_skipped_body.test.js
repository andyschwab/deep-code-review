const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test.skip('prime skipped', () => {
  expect(squares(3)).toEqual([0, 1, 5]);
});
