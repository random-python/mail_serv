"""
"""

import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['LOGGING_FILE_DIR'] = f'{THIS_DIR}/tmp/logger'
