import logging
from datetime import datetime
import os
def setup_logger():
    # logs directory 
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/app_{datetime.now().date()}.log'),
            logging.StreamHandler()
        ]
    )
