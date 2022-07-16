import os
import asyncio
import argparse
import subprocess

from lib.constants import *
from lib.exceptions import *
from lib.recursive_namespace import RecursiveNamespace
from lib.logger_manager import LoggerManager
from lib.session import Session
from lib.config import Config

from novacancy.tunnel_client import NoVacancyTunnelClient

class MySession(Session):
    def __init__(self, args):
        super().__init__()

        # properties for session arguments
        self.args = args

        # absolute paths for base and overlay config files
        self.config_path = os.path.abspath("config/config.yaml")

        self.config = Config()  # contains system config
        self._load_config()  # pulls parameters from disk into config objects
        self.logger = self._init_log()  # initializes log object. Only call this once!!

        # wrapper for arduino interactions including Fuse stepper encoders
        self.tunnel = NoVacancyTunnelClient(self.logger)

    def start(self):
        """start relevant subsystems to fully initialize them"""
        self.tunnel.start()

        self.logger.info("Session started!")

    def _load_config(self):
        """Load config files from disk using previously defined paths into session properties"""
        self.config = Config.from_file(self.config_path)
    
    def set_config(self, key: str, value):
        value = type(self.config.get_nested(key.split("/")))(value)
        self.config.set_nested(key.split("/"), value)
        self.config.save()

    def _init_log(self):
        """Call the LoggerManager get_logger method to initialize logger. Only call once!"""
        return LoggerManager.get_logger(self.config.log)

    def stop(self, exception):
        """
        Fully shutdown appropriate subsystems.
        """
        self.tunnel.stop()  # shuts down serial communication
        if exception is not None:
            self.logger.error(exception, exc_info=True)


async def update_tunnel(session: MySession):
    """
    Task to call tunnel.update (arduino communications) in a loop
    :param session: instance of MySession
    """
    tunnel = session.tunnel
    while True:
        await tunnel.update()
        await asyncio.sleep(0.005)


async def ping_tunnel(session: MySession):
    tunnel = session.tunnel
    while True:
        tunnel.write_ping()
        await asyncio.sleep(0.5)



def main():
    """Where the show starts and stops"""
    parser = argparse.ArgumentParser(description="home-delivery-bot")

    # parser.add_argument("--cli",
    #                     action="store_true",
    #                     help="If this flag is present, enable CLI")
    cmd_args = parser.parse_args()

    args = RecursiveNamespace()
    args.cli = cmd_args.cli

    session = MySession(args)

    # add relevant asyncio tasks to run
    session.add_task(update_tunnel(session))
    if args.cli:
        session.add_task(session.cli.run())

    session.run()  # blocks until all tasks finish or an exception is raised


if __name__ == "__main__":
    main()
