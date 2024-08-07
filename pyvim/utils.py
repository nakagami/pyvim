import re


def re_finditer(sub, text, flags):
    try:
        iterator = re.finditer(sub, text, flags)
    except re.error:
        iterator = re.finditer(re.escape(sub), text, flags)

    return iterator
