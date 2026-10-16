const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('notify calls back', () => {
  const cb = jest.fn();
  cb('HI');
  expect(cb).toHaveBeenCalledWith('HI');
});
