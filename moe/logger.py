import logging


def log():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.INFO)

    handler = logging.StreamHandler()
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


if __name__ == '__main__':
    log()
