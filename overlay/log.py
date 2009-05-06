from logging import getLogger

logger = getLogger('overlay')
logger_controller = getLogger('overlay.controller')
logger_connector = getLogger('overlay.connector')
logger_publisher = getLogger('overlay.publisher')
logger_connection = getLogger('overlay.connection')
logger_bt = getLogger('overlay.protocols.bt')

loggers = (
    logger, logger_controller, logger_connector,
    logger_publisher, logger_connection
    )
