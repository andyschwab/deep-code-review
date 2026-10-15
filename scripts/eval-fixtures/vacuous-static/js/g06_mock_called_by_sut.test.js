const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('notify uppercases', () => {
  const cb = jest.fn();
  notify(cb, 'hi');
  expect(cb).toHaveBeenCalledWith('HI');
});
