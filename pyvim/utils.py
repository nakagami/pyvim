import re
import logging


def re_finditer(sub, text, flags):
    try:
        iterator = re.finditer(sub.replace(r"\<", r"\b(?=\w)").replace(r"\>", r"\b(?<=\w)"), text, flags)
    except re.error:
        iterator = re.finditer(re.escape(sub), text, flags)

    return iterator


def getLogger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.FileHandler("./pyvim.log"))

