import datetime
import sys
import os
import threading
import errno


COLOUR_ENABLED = False
try:
    import colours
    COLOUR_ENABLED = True

except ImportError:
    pass

# Debug levels in descending levels of detail.
# (priority, txt-colour, bg-colour)
DEBUG = (10, "blue", None, "DEBUG")
INFO = (20, "green", None, "INFO")
WARNING = (30, "yellow", None, "WARNING")
ERROR = (40, "red", None, "ERROR")
CRITICAL = (50, "red", "white", "CRITICAL")


def get_datetime():
    return datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")


def get_date():
    return datetime.datetime.now().strftime("%d-%m-%Y")


def get_time():
    return datetime.datetime.now().strftime("%H:%M:%S")


def _get_caller():
    try:
        return sys._getframe(3).f_code.co_name

    except ValueError:
        return sys._getframe(2).f_code.co_name


def _get_caller_file():
    try:
        path = sys._getframe(3).f_code.co_filename

    except ValueError:
        path = sys._getframe(2).f_code.co_filename

    return os.path.basename(path)


def create_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class Logger(object):
    """
    Handles logging.
    """
    def __init__(self, log_dir_or_path, one_file_mode=False, file_level=DEBUG, stdout_level=INFO, verbose=True, colour=COLOUR_ENABLED, threaded=True):
        """
        Params:

        log_dir_or_path: the directory to put the logfiles if one_file_mode is False, otherwise the path to the logfile.
        one_file_mode: if True, appends to existing logfile. If False, creates a new logfile in specified directory.
        file_level: the maximum level of detail outputted to the logfile.
        stdout_level: the maximum level of detail outputted to stdout (has no effect if verbose=False).
        verbose: determines if logging is outputted to stdout in addition to the logfile.
        colour: enable the use of codes for coloured text in a terminal. Can't be changed once Logger object has been instantiated.
        threaded: whether the file writing is handled by a separate thread.
        """
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

            self.logfile.flush()
            os.fsync(self.logfile.fileno())

        else:
            create_path(log_dir_or_path)

            filename = get_date() + "@" + get_time() + ".log"
            filename = filename.replace("/", "-")
            if os.name == "nt":
                filename = filename.replace(":", "-")

            self.logfile = open(os.path.join(log_dir_or_path, filename), "a+")

            self.logfile.write("{} New {} session, logging started.\n\n".format(get_datetime(), _get_caller_file()))
            self.logfile_path = os.path.join(log_dir_or_path, filename)

            self.logfile.flush()
            os.fsync(self.logfile.fileno())

        self.file_level = file_level
        self.stdout_level = stdout_level
        self.verbose = verbose
        self.threaded = threaded
        
        try:
            if colour:
                self._writer = colours.ColoredWriter()
                self._writer.on_colour = None
        
        except NameError:
            pass

    def log(self, data, level):
        if level[0] < self.file_level[0] and level[0] < self.stdout_level[0]:
            return

        now = get_time()

        if level != INFO:
            to_log = now + " Caller: " + str(_get_caller()) + ", " + str(_get_caller_file())

        else:
            to_log = now

        # Create a newline after the date/time unless the level is info
        if level != INFO:
            to_log += "\n"

        else:
            to_log += " "

        to_log += data + "\n"

        if self.verbose and not level[0] < self.stdout_level[0]:
            try:
                self._writer.write(to_log, self.stdout_level[1], self.stdout_level[2])

            except AttributeError:
                print(to_log)

        if not level[0] < self.file_level[0]:
            def write():
                self.logfile.write(to_log+"\n")
                self.logfile.flush()
                os.fsync(self.logfile.fileno())

                return

            if self.threaded:
                try:
                    the_thread = threading.Thread(target=write)
                    the_thread.start()

                except RuntimeError:
                    write()

            else:
                write()

    def debug(self, data):
        self.log("DEBUG: " + data, DEBUG)

    def info(self, data):
        self.log("INFO: " + data, INFO)

    def warning(self, data):
        self.log("WARNING: " + data, WARNING)

    def error(self, data):
        self.log("ERROR: " + data, ERROR)

    def critical(self, data):
        self.log("CRITICAL: " + data, CRITICAL)

logger = None


def start_logging_session(log_dir_or_path=os.path.join("logs", "game"), one_file_mode=False, file_level=DEBUG,
                          stdout_level=INFO, verbose=True, colour=COLOUR_ENABLED, threaded=True):
    global logger

    if logger is None:
        logger = Logger(log_dir_or_path, one_file_mode, file_level, stdout_level, verbose, colour, threaded)

    else:
        # logging session already started!
        pass

    return logger