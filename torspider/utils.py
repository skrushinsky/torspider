import os
import hashlib
from io import BytesIO
from PIL import Image
import logging


def make_digest(s):
    m = hashlib.md5()
    m.update(s.encode('utf-8'))
    return m.hexdigest()


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_screenshot(imgdata, url=None, screenshots_dir=None):
    img = Image.open(BytesIO(imgdata))
    digest = make_digest(url)
    fname = '{}.png'.format(digest[2:])
    di = os.path.join(screenshots_dir, digest[:2])
    path = os.path.join(di, fname)
    ensure_dir(di)
    assert not os.path.isfile(path), 'File %s exists!' % path
    img.save(path)
    logging.info('Screenshot for %s saved as %s.', url, path)
    return os.path.join(digest[:2], fname)


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
