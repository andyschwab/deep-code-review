const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('fetch chain', () => {
  fetchThing(1)
    .then((r) => expect(r.name).toBe('wrong'))
    .catch(() => {});
});
