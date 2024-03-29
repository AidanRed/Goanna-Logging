"""
Need a way of stopping streams from blocking if queue.get() is called after last log message but before main thread ends
Add verbosity levels.
Fix threaded file writing
Stdout needs level
"""
import datetime
import sys
import os
import threading
import errno
import io
import functools
from queue import Queue
from collections import namedtuple

try:
    import colorama
    colorama.init()
    COLOUR_ENABLED = True

except ModuleNotFoundError:
    COLOUR_ENABLED = False

# Debug levels in descending levels of detail.
# (priority, txt-colour, bg-colour)

Verbosity = namedtuple("Verbosity", ("level", "name", "fg_colour", "bg_colour"))
# Make fg_colour and bg_colour optional fields
Verbosity.__new__.__defaults__ = ("", "")

if COLOUR_ENABLED:
    DEBUG = Verbosity(level=10, name="DEBUG", fg_colour=colorama.Fore.BLUE)
    INFO = Verbosity(level=20, name="INFO", fg_colour=colorama.Fore.GREEN)
    WARNING = Verbosity(level=30, name="WARNING", fg_colour=colorama.Fore.YELLOW)
    ERROR = Verbosity(level=40, name="ERROR", fg_colour=colorama.Fore.RED)
    CRITICAL = Verbosity(level=50, name="CRITICAL", fg_colour=colorama.Fore.RED, bg_colour=colorama.Fore.WHITE)

else:
    DEBUG = Verbosity(level=10, name="DEBUG")
    INFO = Verbosity(level=20, name="INFO")
    WARNING = Verbosity(level=30, name="WARNING")
    ERROR = Verbosity(level=40, name="ERROR")
    CRITICAL = Verbosity(level=50, name="CRITICAL")


def get_datetime():
    return datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")


def get_date():
    return datetime.datetime.now().strftime("%d-%m-%Y")


def get_time():
    return datetime.datetime.now().strftime("%H:%M:%S")


def _get_frames():
    frames = []
    i = 0
    while True:
        try:
            frames.append(sys._getframe(i))

        except ValueError:
            break

        i += 1

    new_frames = []
    # Possible optimisation
    for frame in frames:
        if os.path.basename(frame.f_code.co_filename) != "goanna_logging.py":
            new_frames.append(frame)

    return new_frames


def _get_caller():
    frames = _get_frames()

    return frames[0].f_code.co_name


def _get_caller_file():
    frames = _get_frames()

    return os.path.basename(frames[0].f_code.co_name)


def _caller_and_path():
    the_frame = _get_frames()[0].f_code

    return the_frame.co_name, os.path.basename(the_frame.co_filename)


def create_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class OutputStream(object):
    def __init__(self, threaded=False):
        self._threaded = threaded

        if self._threaded:
            self.queue = Queue()
            self._thread = threading.Thread(target=self.__emission_loop, daemon=False)
            self._thread.start()

    def __emission_loop(self):
        while threading.main_thread().is_alive():
            self.emit(self.queue.get())

        # Ensure all data is written
        while not self.queue.empty():
            self.emit(self.queue.get())

        self.close()

    def write(self, data):
        if self._threaded:
            self.queue.put(data)

        else:
            self.emit(data)

    def emit(self, data):
        pass

    def force_sync(self):
        pass

    def close(self):
        pass


class StdoutStream(OutputStream):
    def __init__(self, path=None, threaded=False, force_write=False):
        self.force_write = force_write
        super().__init__(threaded=threaded)

    def emit(self, data):
        print(data, end="", flush=self.force_write)

    def force_sync(self):
        sys.stdout.flush()

    def close(self):
        pass


class FileStream(OutputStream):
    def __init__(self, log_dir_or_path, one_file_mode=False, threaded=True, force_write=False):
        if one_file_mode:
            self.logfile_path = log_dir_or_path
            the_dir = self.logfile_path.rstrip(os.path.basename(self.logfile_path))
            create_path(the_dir)

            try:
                logfile = open(log_dir_or_path, "r")
                data = logfile.read().strip()
                logfile.close()

            except FileNotFoundError:
                data = ""

            # Open the file for reading and appending. It is created if it doesn't already exist.
            self.logfile = open(log_dir_or_path, "a+")

            if data == "":
                self.logfile.write("{} New {} session, logging started.\n\n".format(get_datetime(), _get_caller_file()))

            else:
                self.logfile.write("\n\n{} New {} session, logging started.\n\n".format(get_datetime(), _get_caller_file()))

        else:
            create_path(log_dir_or_path)

            filename = "{}@{}.log".format(get_date(), get_time())
            filename = filename.replace("/", "-")
            if os.name == "nt":
                filename = filename.replace(":", "-")

            self.logfile_path = os.path.join(log_dir_or_path, filename)
            self.logfile = open(self.logfile_path, "a+")

            self.logfile.write("{} New {} session, logging started.\n\n".format(get_datetime(), _get_caller_file()))

        self.force_sync()

        self.force_write = force_write

        super().__init__(threaded=threaded)

    def emit(self, data):
        self.logfile.write(data)
        self.logfile.flush()
        if self.force_write:
            os.fsync(self.logfile.fileno())

    def force_sync(self):
        os.fsync(self.logfile.fileno())

    def close(self):
        self.logfile.close()


# Sync interval?
class CachedStream(OutputStream):
    def __init__(self, path, threaded=False):
        self.cache = io.StringIO()
        self.output_file = FileStream(path, threaded=False)

        super().__init__(threaded=threaded)

    def emit(self, data):
        self.cache.write(data)

    def force_sync(self):
        self.output_file.write(self.cache.getvalue())
        self.cache.close()
        self.cache = io.StringIO()

    def close(self):
        self.output_file.write(self.cache.getvalue())
        self.cache.close()
        self.output_file.close()


class Logger(object):
    """
    Handles logging.
    """
    def __init__(self, output_streams=((StdoutStream, DEBUG),), verbose=True, threaded=True):
        """
        Parameters:

        log_dir_or_path: the directory to put the logfiles if one_file_mode is False, otherwise the path to the logfile.
        one_file_mode: if True, appends to existing logfile. If False, creates a new logfile in specified directory.
        file_level: the maximum level of detail outputted to the logfile.
        stdout_level: the maximum level of detail outputted to stdout (has no effect if verbose=False).
        verbose: determines if logging is outputted to stdout in addition to the logfile.
        colour: enable the use of codes for coloured text in a terminal. Can't be changed once Logger object has been instantiated.
        threaded: whether the file writing is handled by a separate thread.
        """
        self.output_streams = output_streams

        self.verbose = verbose
        self.threaded = threaded

    def log(self, data, level):
        data = "%s: " % (level.name,)

        now = get_time()

        if level != INFO:
            caller, caller_path = _caller_and_path()
            to_log = "%s Caller: %s, %s\n%s\n" % (now, str(caller), str(caller_path), data)

        else:
            to_log = "%s %s\n" % (now, data)

        for stream, stream_level in self.output_streams:
            if not level.level < stream_level.level:
                stream.emit("%s\n" % (to_log,))

    def force_sync(self):
        """
        Force the all the data held in buffer to be written to disk. Very slow.

        Returns: None
        """
        for stream in self.output_streams:
            stream[0].force_sync()

    debug = functools.partialmethod(log, level=DEBUG)
    info = functools.partialmethod(log, level=INFO)
    warning = functools.partialmethod(log, level=WARNING)
    error = functools.partialmethod(log, level=ERROR)
    critical = functools.partialmethod(log, level=CRITICAL)


class DebugClass(object):
    def __init__(self, methods_to_log=(), attributes_to_log=(), log_level=DEBUG):
        self.LOG_METHODS = methods_to_log
        self.LOG_ATTRIBUTES = attributes_to_log
        self.LOG_LEVEL = log_level

    def __getattr__(self, item):
        to_return = super().__getattribute__(item)
        if item in self.LOG_ATTRIBUTES:
            logger.log("%s accessing %s" % (_get_caller(), item))

        return to_return

    def __setattr__(self, *args, **kwargs):
        pass


def func_logger(func, to_watch=(), log_level=DEBUG):
    if not func:
        return functools.partial(func_logger, to_watch=to_watch, log_level=log_level)

    func_parameters = func.__code__.co_varnames

    @functools.wraps(func)
    def new_f(*args, **kwargs):
        to_display = []

        for arg_num, arg in enumerate(args):
            arg_name = func_parameters[arg_num]
            if arg_name in to_watch:
                to_display.append((arg_name, arg))

        for key, value in kwargs.items():
            if key in to_watch:
                to_display.append((key, value))

        if not to_display:
            logger.log("%s called." % (func.__name__,), log_level)

        else:
            the_string = "%s called with args: "
            for key, value in to_display:
                the_string += "{}: {}".format(key, value)

            logger.log(the_string)

        return func(*args, **kwargs)

    return new_f

logger = None


def start_logging_session(log_dir_or_path=os.path.join("logs"), one_file_mode=False, file_level=DEBUG,
                          stdout_level=INFO, verbose=True, threaded=False):
    global logger

    if logger is None:
        stream = FileStream(log_dir_or_path, one_file_mode, threaded)
        logger = Logger(((StdoutStream(), stdout_level), (stream, file_level)), verbose, threaded)

    else:
        # logging session already started!
        pass

    return logger
