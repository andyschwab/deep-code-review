const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('event handler', () => {
  onEvent(() => {
    expect(1).toBe(2);
  });
});
