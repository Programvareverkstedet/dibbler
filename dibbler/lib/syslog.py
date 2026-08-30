import logging
import logging.handlers

SYSLOG_ADDRESS = "/dev/log"


def get_syslog_logger(name: str = "dibbler") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    try:
        handler = logging.handlers.SysLogHandler(address=SYSLOG_ADDRESS)
    except OSError:
        # Fallback logger with no handlers.
        return logger

    handler.ident = f"{name}: "
    logger.addHandler(handler)
    return logger
