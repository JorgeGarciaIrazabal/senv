import logging


logging.basicConfig(format='%(asctime)s-%(levelname)s-%(message)s', level=logging.INFO)
logging.warning('This is a Warning')
log = logging.getLogger(__name__)
