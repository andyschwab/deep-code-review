const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('parse error message', () => {
  expect.assertions(1);
  try {
    parseInt10('x1');
  } catch (e) {
    expect(e.message).toContain('x1');
  }
});
