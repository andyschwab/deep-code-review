const { add, clamp, parseInt10, notify, fetchThing, squares, onEvent } = require('./sut');

test('notify via done', (done) => {
  notify((m) => {
    expect(m).toBe('YO');
    done();
  }, 'yo');
});
