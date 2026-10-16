const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('fetch resolves', () => {
  return expect(fetchThing(1)).resolves.toEqual({ id: 1, name: 'thing1' });
});
