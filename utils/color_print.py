class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def warning(msg):
    print(bcolors.WARNING + msg + bcolors.ENDC)

def success(msg):
    print(bcolors.OKGREEN + msg + bcolors.ENDC)

def fail(msg):
    print(bcolors.FAIL + msg + bcolors.ENDC)

def info(msg):
    print(bcolors.OKBLUE + msg + bcolors.ENDC)
