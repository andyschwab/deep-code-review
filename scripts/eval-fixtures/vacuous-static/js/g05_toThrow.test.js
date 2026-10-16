const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('parse rejects text', () => {
  expect(() => parseInt10('abc')).toThrow('bad int');
});
