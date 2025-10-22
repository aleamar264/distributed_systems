import logging

def configure_logging(level: int = logging.INFO):
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    logging.basicConfig(level=level, format=fmt)
    # return root logger for convenience
    return logging.getLogger()
