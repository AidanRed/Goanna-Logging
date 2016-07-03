import datetime
import sys
import os
import threading


COLOUR_ENABLED = False
try:
    import colours
    COLOUR_ENABLED = True

except ImportError:
    pass

# Debug levels in descending levels of detail.
# (priority, txt-colour, bg-colour)
DEBUG = (10, "blue", None)
INFO = (20, "green", None)
WARNING = (30, "yellow", None)
ERROR = (40, "red", None)
CRITICAL = (50, "red", "white")


def get_datetime():
    return datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")


def get_time():
    return datetime.datetime.now().strftime("%H:%M:%S")


def _get_caller():
    try:
        return sys._getframe(3).f_code.co_name

    except ValueError:
        return sys._getframe(2).f_code.co_name


def _get_caller_file():
    try:
        return sys._getframe(3).f_code.co_filename

    except ValueError:
        return sys._getframe(2).f_code.co_filename


class Logger(object):
    """
    Handles logging.
    """
    def __init__(self, log_dir_or_path, one_file_mode=False, file_level=INFO, stdout_level=INFO, verbose=True, colour=COLOUR_ENABLED, threaded=True):
        """
        Params:

        log_dir_or_path: the directory to put the logfiles if one_file_mode is False, otherwise the path to the logfile.]
        one_file_mode: if True, appends to existing logfile. If False, creates a new logfile in specified directory.
        file_level: the maximum level of detail outputted to the logfile.
        stdout_level: the maximum level of detail outputted to stdout (has no effect if verbose=False).
        verbose: determines if logging is outputted to stdout in addition to the logfile.
        colour: enable the use of codes for coloured text in a terminal. Can't be changed once Logger object has been instantiated.
        threaded: whether the file writing is handled by a seperate thread.
        """
        if one_file_mode:
            self.logfile_path = log_dir_or_path

            try:
                logfile = open(log_dir_or_path, "r")
                data = logfile.read().strip()
                logfile.close()

            except FileNotFoundError:
                data = ""

            # Open the file for reading and appending. It is created if it doesn't already exist.
            logfile = open(log_dir_or_path, "a+")

            if data == "":
                logfile.write("{} New {} session, logging started.\n".format(get_datetime(), _get_caller_file()))

            else:
                logfile.write("\n\n{} New {} session, logging started.\n".format(get_datetime(), _get_caller_file()))

            logfile.close()

        else:
            filename = get_datetime() + ".log"
            logfile = open(filename, "a+")

            logfile.write("{} New {} session, logging started.\n".format(get_datetime(), _get_caller_file()))
            logfile.close()

            self.logfile_path = os.path.join(log_dir_or_path, filename)


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

        to_log += data

        if self.verbose and not level[0] < self.stdout_level[0]:
            try:
                self._writer.write(to_log, self.stdout_level[1], self.stdout_level[2])

            except AttributeError:
                print(to_log)

        if not level[0] < self.file_level[0]:
            def write():
                logfile = open(self.logfile_path, "a+")
                logfile.write(to_log)
                logfile.close()

            if self.threaded:
                the_thread = threading.Thread(target=write)
                the_thread.start()

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
