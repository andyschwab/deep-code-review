def add(a, b):
    return a + b


def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def parse_int(s):
    if not s.strip().lstrip("-").isdigit():
        raise ValueError("bad int: " + s)
    return int(s)


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def notify(cb, msg):
    cb(msg.upper())


def squares(n):
    return [i * i for i in range(n)]


def save(path, text):
    path.write_text(text.strip())


def load(path):
    return path.read_text()
