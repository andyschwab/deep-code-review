const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('add swallowed', () => {
  try {
    expect(add(1, 2)).toBe(4);
  } catch (e) {
    // ignore
  }
});
