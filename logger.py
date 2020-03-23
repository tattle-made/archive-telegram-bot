from datetime import datetime

def log(data):
    print('----', datetime.now(), '----')
    print(data)


def logError(error):
    print('****', datetime.now(), '****')
    print(error)