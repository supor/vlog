#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#
import os
import sys
from config import PORT, MONGO_DB_HOST, MONGO_DB_NAME
from core.app import load_apps, settings
from core.utest import run_utest as utest_func
from core.util import get_logger

from tornado.web import Application
from tornado.ioloop import IOLoop

def main(port = None):
    port = port if port else PORT
    logger = get_logger()
    info = ''
    info += 'Running On Port: %s\n' % port
    apps = load_apps()
    for k, v in apps.items():
        info += '\t%-20s %s\n' % (k , v)
    logger.info(info)
    if settings.get('debug', False):
        logger.warn('Debug Mode is On')
    app = Application(apps.items(), **settings)
    app.listen(port)
    IOLoop.instance().start()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser('pec_run.py')
    parser.add_argument('-u', '--utest', action='store', nargs='?',
                        default = '', help = 'Run unit test')
    parser.add_argument('-p', '--port', action='store', nargs='?',
                        default=PORT, type=int,
                        help = 'Port to listen to')
    parser.add_argument('-c', '--clear', action='store_true', dest='clear',
                        default= False, help = "Clear tmp file")
    parser.add_argument('-m', '--mongo', action='store_true', dest='mongo',
                        default = False, help = "Open the mongo shell")
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        default = False, help = 'Run pec with debug mode')


    args = parser.parse_args()
    if args.clear:
        cmd = "find ./ -name '*.py[co]' -exec rm -rf {} \;"
        print 'Clear tmp files...'
        os.system(cmd)
        sys.exit(0)

    if args.mongo:
        cmd = "mongo {0}/{1}".format(MONGO_DB_HOST, MONGO_DB_NAME)
        os.system(cmd)
        sys.exit(0)

    if args.utest is None or args.utest:
        utest_func(args.utest)
    else:
        try:
            if args.debug: settings.update(debug = True)
            main(args.port)
        except KeyboardInterrupt:
            print 'exiting...'
