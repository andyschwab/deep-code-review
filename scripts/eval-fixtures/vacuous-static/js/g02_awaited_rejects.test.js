const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('fetch rejects negative', async () => {
  await expect(fetchThing(-1)).rejects.toThrow('neg id');
});
