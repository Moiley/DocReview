import concurrent.futures

from config.config import MAX_WORKS
from utils.logger import logger


class TaskThreadPool(object):

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKS)
        self.worker = None

    def thread_run(self, func, args):
        self.worker = self.executor.submit(lambda params: func(*params), args)
        self.worker.add_done_callback(lambda func: func.result())
        self.worker.add_done_callback(lambda func: self.handle_exception())

    def handle_exception(self, exc):
        if exc:
            logger.error(type(exc), exc, exc.__traceback__)