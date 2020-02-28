from datetime import datetime

def log(data):
    print('----------------------------')
    print(datetime.now())
    print(data)
    print('----------------------------')


def logError(error):
    print('****************************')
    print(datetime.now())
    print(error)
    print('****************************')