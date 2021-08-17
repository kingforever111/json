import zmq
from pathlib import Path
from itertools import count


def initLog(fname):
    from loguru import logger

    LOG_DIR = Path(__file__).resolve().parent / 'zmq_server' / fname
    LEVEL_LIST = ['INFO']
    # LEVEL_LIST = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']

    logger.remove()
    for level in LEVEL_LIST:
        logger.add(
            LOG_DIR / f'{level}.log', rotation='1 week',
            format='{time:YYYY-MM-DD at HH:mm:ss} {level} {message}', level=level, enqueue=True
        )

    return LOG_DIR, logger

def launch(port, fname):
    log_dir, logger = initLog(fname)
    ctx = zmq.Context()
    skt = ctx.socket(zmq.PULL)
    skt.bind('tcp://*:%d' % port)

    print('Start Port: %d LogPath: %s' % (port, log_dir))
    for i in count(1):
        msg = skt.recv_json()
        logger.info('index[%d]: %s' % (i, msg))


if __name__ == '__main__':
    from multiprocessing import Process

    maps = {
        # Port: Street or road name
        # e.g.: 5566: 'hainalu'
    }

    for port, fname in maps.items():
        Process(target=launch, args=(port, fname)).start()

