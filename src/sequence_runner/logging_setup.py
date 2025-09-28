import logging

def setup_logging(level=logging.INFO):
    fmt = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=level, format=fmt)
    return logging.getLogger(__name__)
