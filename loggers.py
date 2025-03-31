import logging

def get_logger(year):
    """Create a logger for each year."""
    log_file = f"logs/log_{year}.txt"  # Log file specific to the year
    logger = logging.getLogger(f"logger_{year}")
    logger.setLevel(logging.DEBUG)
    
    # Check if a handler already exists to avoid adding multiple handlers
    if not logger.hasHandlers():
        handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_error(year, message, book=None):
    logger = get_logger(year)
    if book:
        logger.error(f"❌ Error processing BOOK: {book} - {message}\n")
        print(f"❌ Error processing BOOK: {book} - {message}")
    else:
        logger.error(f'❌ {message}\n')
        print(f'❌ {message}')

def log_info(year, message):
    logger = get_logger(year)
    logger.info(message)


