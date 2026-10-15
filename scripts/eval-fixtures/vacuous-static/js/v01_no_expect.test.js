const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('add runs', () => {
  add(1, 2);
});
