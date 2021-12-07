# -*- coding: utf-8 -*-
""" Basic logging utilities. """

import os
import sys
import logging
from datetime import datetime


def setup_logging(name: str == __name__, log_level: str = None, to_file: bool = True) -> logging.Logger:
    """ Setup basic logging. """
    
    # Define logger
    logger = logging.getLogger(name)
    
    # Set up log level and format
    log_level_init = logging.DEBUG if log_level=='debug' else logging.INFO
    log_format = '%(asctime)s %(levelname)s: %(message)s'
    
    if to_file and 'ipykernel' not in sys.modules:
        log_filename = '{}_{}.log'.format(datetime.now().strftime('%Y%m%d-%H%M%S'), 'data_processing')
        log_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), log_filename)
        log_file_handler = logging.FileHandler(log_filepath, 'a', 'utf-8')
        log_file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(log_file_handler)
        logger.setLevel(log_level_init)
    else:
        logging.basicConfig(format=log_format, level=log_level_init)

    return logger
