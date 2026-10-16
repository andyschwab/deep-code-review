const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('fetch returns thing', async () => {
  const r = await fetchThing(3);
  expect(r).toEqual({ id: 3, name: 'thing3' });
});
