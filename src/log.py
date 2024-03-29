import inspect
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logger = None


def start_logger():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter(
        "%(asctime)s|[%(levelname)8s]|[%(module)s.%(name)s.%(funcName)s]|%(lineno)4s|%(message)s"
    )
    log_path = Path(__file__).parent.joinpath("log")
    if not os.path.isdir(log_path):
        os.makedirs(log_path)
    file_name = log_path.joinpath(
        "log_{}.log".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    )
    file_handler = logging.FileHandler(filename=file_name, mode="a")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)


def print_exception(e: object):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    file_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    short_message = (
        f"Exception at {exc_type} - {file_name} - {exc_tb.tb_lineno}\n"
        f"Calling Function: {inspect.stack()[1][3]}"
    )
    message = f"{short_message}\n{str(e)}"
    logger.debug(message)


# Initialize Logger
start_logger()
