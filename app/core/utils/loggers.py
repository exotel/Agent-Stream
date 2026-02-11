import logging

class LoggerFactory:
    _logger = None
    def get_logger(self, name=None):
        if self._logger is None:
            self._logger = logging.getLogger(name or "exotel.wss")
            if not self._logger.handlers:
                h = logging.StreamHandler()
                h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
                self._logger.addHandler(h)
                self._logger.setLevel(logging.INFO)
        return self._logger
