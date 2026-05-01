# A dictionary to hold all exposed functions.
_exposed_functions = {}


def expose(func):
    """Decorator that registers a function as exposed."""
    _exposed_functions[func.__name__] = func
    return func


def get_exposed():
    """Return the dictionary of exposed functions."""
    return _exposed_functions
