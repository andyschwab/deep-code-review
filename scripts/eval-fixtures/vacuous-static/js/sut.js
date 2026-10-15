exports.add = (a, b) => a + b;
exports.clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
exports.parseInt10 = (s) => {
  if (!/^-?\d+$/.test(s.trim())) throw new Error('bad int: ' + s);
  return parseInt(s, 10);
};
exports.notify = (cb, msg) => cb(msg.toUpperCase());
exports.fetchThing = async (id) => {
  if (id < 0) throw new Error('neg id');
  return { id, name: 'thing' + id };
};
exports.squares = (n) => Array.from({ length: n }, (_, i) => i * i);
exports.onEvent = (cb) => { void cb; };
