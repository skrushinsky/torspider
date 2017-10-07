import os
from tornado.iostream import PipeIOStream

class SafeFileIOStream:
    """Asynchroneous file writer.

    Usage example:

    with SafeFileIOStream('/tmp/test.txt') as stream:
        await stream.write(b'hello world')
    """
    def __init__(self, fname):
        self.fname = fname

    def __enter__(self):
        # Create file
        os.open(self.fname, os.O_CREAT)
        # Create stream
        fd = os.open(self.fname, os.O_WRONLY)
        self.stream = PipeIOStream(fd)
        return self.stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close stream
        self.stream.close()
