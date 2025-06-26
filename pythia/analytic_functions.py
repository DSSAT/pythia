__license__ = "BSD-3-Clause"

def generate_funs(config):
    funcs = []
    for key, funs in config.items():
        fun = {}
        f, *args = funs.split("::")
        fun["key"] = key
        fun["args"] = args
        if f == "subtract":
            fun["fun"] = subtract
        if f == "from_config":
            pass
        funcs.append(fun)
    return funcs


def subtract(terms):
    a = _numberify_term(terms[0])
    b = _numberify_term(terms[1])
    return a - b


def _numberify_term(term):
    if "." in term:
        return float(term)
    else:
        return int(term)


def from_config(terms):
    lat = _numberify_term(terms[0])
    lng = _numberify_term(terms[1])
    return lat + lng
