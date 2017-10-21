import os

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def iter_file(path):
    '''Open a text file, read it line by line, yielding
    stripped line provided that it is not empy and does not start with '#'
    '''
    with open(path, mode='rt') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            yield line
