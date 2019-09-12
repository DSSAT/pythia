def generate_funs(config):
    funcs = []
    for key,funs in config.items():
        fun = {}
        f, *args = funs.split("::")
        if (f == "subtract"):
            fun['fun'] = subtract
        fun['key'] = key
        fun['args'] = args
        funcs.append(fun)
    return funcs


def subtract(terms):
    a = _numberify_term(terms[0])
    b = _numberify_term(terms[1])
    return a-b


def _numberify_term(term):
    if "." in term:
        return float(term)
    else:
        return int(term)
