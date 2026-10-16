const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('fetch awaited', async () => {
  await fetchThing(1);
});
