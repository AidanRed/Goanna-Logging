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

class Logger(object):
    """
    Handles logging. Can log to multiple files simultaneously.
    """
    def __init__(self, filepaths=[], file_level=INFO, stdout_level=INFO, verbose=True, colour=False):
        """
        Params:

        filepaths: list of files to log to.
        file_level: the maximum level of detail outputted to the logfile.
        stdout_level: the maximum level of detail outputted to stdout (has no effect if verbose=False).
        verbose: determines if logging is outputted to stdout in addition to the logfile.
        colour: enable the use of codes for coloured text in a terminal. Can't be changed once Logger object has been instantiated.
        """
        self.logfiles = []
        for file in filepaths:
            #Open the file for reading and appending. It is created if it doesn't already exist.
            self.logfiles.append(open(file, mode="a+"))

        self.file_level = file_level
        self.stdout_level = stdout_level
        self.verbose = verbose

        if colour:
            self._writer = colours.ColoredWriter()
            self._writer.on_colour = None

    def log(self, data, level):
        if level < self.file_level and level < self.stdout_level:
            return

        now = get_datetime()
        to_log = now + " " + sys._getframe(1)

        #Create a newline after the date/time unless the level is info
        if level != INFO:
            to_log += "\n"

        else:
            to_log += ": "

        to_log += data

        if self.verbose and not level < self.stdout_level[0]:
            try:
                self._writer.write(to_log, self.stdout_level[1], self.stdout_level[2])

            except AttributeError:
                print(to_log)

        if not level < self.file_level[0]:
            #TODO: Possibly make this run on a seperate thread for speed reasons - likely to help most when logging over network
            for logfile in self.logfiles:
                logfile.write(to_log)

    def debug(self, data):
        self.log(data, DEBUG)

    def info(self, data):
        self.log(data, INFO)

    def warning(self, data):
        self.log(data, WARNING)

    def error(self, data):
        self.log(data, ERROR)

    def critical(self, data):
        self.log(data, CRITICAL)