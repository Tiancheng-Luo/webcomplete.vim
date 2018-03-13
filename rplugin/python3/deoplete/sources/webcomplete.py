'''Web completion of words for Neovim
This plugin works with Neovim and Deoplete, allowing you to
complete words from your Chrome instance in your editor.'''

from os.path import dirname, abspath, join, pardir
from subprocess import check_output, PIPE
from threading import Thread
from queue import Queue, Empty

from .base import Base
import deoplete.util


def log(msg):
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S,%f")
    with open('/tmp/deoplete-webcomplete.log', 'a') as file_:
        file_.write('%s %s\n' % (timestamp, msg))


class Source(Base):
    def __init__(self, vim):
        super().__init__(vim)
        self.__last_input = None
        self.__cache = None

        self.name = 'webcomplete'
        self.kind = 'keyword'
        self.mark = '[web]'
        self.rank = 4
        filedir = dirname(abspath(__file__))
        projectdir = abspath(join(filedir, pardir, pardir, pardir, pardir))
        self.__script = join(projectdir, 'sh', 'webcomplete')
        self._tasks = Queue()
        self._thread = Thread(target=self.background_thread, daemon=True)
        self._thread.start()

    def background_thread(self):
        while True:
            input_ = self._tasks.get()
            output = check_output(self.__script.split(), shell=True)
            candidates = output.decode('utf-8').splitlines()
            self.__cache = [{'word': word} for word in candidates]

            # Clear the queue
            while not self._tasks.empty():
                try:
                    self._tasks.get(block=False)
                except Empty:
                    break

    def gather_candidates(self, context):
        if not self._is_same_context(context['input']):
            log('Reset cache: %s' % context['input'])
            self.__last_input = context['input']
            # The input has changed, notify background thread to fetch new words
            self._tasks.put(self.__last_input)

        if self.__cache is not None:
            # Return what we have now, though results may be a bit outdated
            context['is_async'] = False
            return self.__cache

        context['is_async'] = True
        return []

    def _is_same_context(self, input):
        return self.__last_input and input.startswith(self.__last_input)
