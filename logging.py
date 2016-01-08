import datetime
import sys
import colours

#Debug levels in descending levels of detail.
#(priority, txt-colour, bg-colour)
DEBUG = (10, "blue", None)
INFO = (20, "green", None)
WARNING = (30, "yellow", None)
ERROR = (40, "red", None)
CRITICAL = (50, "red", "white")

def get_datetime():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

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
    Handles logging. Can log to multiple files simultaneously.
    """
    def __init__(self, filepaths=(), file_level=INFO, stdout_level=INFO, verbose=True, colour=True):
        """
        Params:

        filepaths: list of files to log to.
        file_level: the maximum level of detail outputted to the logfile.
        stdout_level: the maximum level of detail outputted to stdout (has no effect if verbose=False).
        verbose: determines if logging is outputted to stdout in addition to the logfile.
        colour: enable the use of codes for coloured text in a terminal. Can't be changed once Logger object has been instantiated.
        """
        assert not isinstance(filepaths, str)

        self.logfiles = filepaths
        for file in filepaths:
            logfile = open(file, "r")
            data = logfile.read().strip()
            logfile.close()

            #Open the file for reading and appending. It is created if it doesn't already exist.
            logfile = open(file, "a+")

            if data == "":
                logfile.write("{} New {} session, logging started.\n".format(get_datetime(), _get_caller_file()))

            else:
                logfile.write("\n\n{} New {} session, logging started.\n".format(get_datetime(), _get_caller_file()))

            logfile.close()

        self.file_level = file_level
        self.stdout_level = stdout_level
        self.verbose = verbose

        if colour:
            self._writer = colours.ColoredWriter()
            self._writer.on_colour = None

    def log(self, data, level):
        if level[0] < self.file_level[0] and level[0] < self.stdout_level[0]:
            return

        now = get_datetime()

        if level != INFO:
            to_log = now + " Caller: " + str(_get_caller()) + ", " + str(_get_caller_file())

        else:
            to_log = now

        #Create a newline after the date/time unless the level is info
        if level != INFO:
            to_log += "\n"

        to_log += data

        if self.verbose and not level[0] < self.stdout_level[0]:
            try:
                self._writer.write(to_log, self.stdout_level[1], self.stdout_level[2])

            except AttributeError:
                print(to_log)

        if not level[0] < self.file_level[0]:
            #TODO: Possibly make this run on a separate thread for speed reasons - likely to help most when logging over network
            for logpath in self.logfiles:
                logfile = open(logpath, "a+")
                logfile.write(to_log)
                logfile.close()

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