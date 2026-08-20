import os
import logging
from dotenv import load_dotenv

load_dotenv()
LOG_LEVEL = int(os.environ.get("LOG_LEVEL"))


def logging_setup():
    class CustomFormatter(logging.Formatter):
        grey = "\x1b[38;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        blue = "\x1b[34;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format_info = "[%(process)d %(levelname)s - %(asctime)s]: "
        format_message = "%(message)s"

        FORMATS = {
            logging.DEBUG: grey + format_info + reset + format_message,
            logging.INFO: blue + format_info + reset + format_message,
            logging.WARNING: yellow + format_info + reset + format_message,
            logging.ERROR: red + format_info + reset + format_message,
            logging.CRITICAL: bold_red + format_info + reset + format_message
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
            return formatter.format(record)

    # Create custom formatter
    custom_formatter = CustomFormatter()

    # Configure the root logger named app
    custom_logger = logging.getLogger('APP')
    custom_logger.setLevel(LOG_LEVEL)

    # set up the console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(custom_formatter)

    # add handlers
    custom_logger.addHandler(console_handler)

    return custom_logger


##
# Setup Logger
logger = logging_setup()
