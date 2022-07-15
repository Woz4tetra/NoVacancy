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
        self.base_config_path = os.path.abspath("config/base.yaml")
        self.overlay_config_path = os.path.abspath("config/robot.yaml")

        self.config = Config()  # contains the combined base and overlay configs
        self.base_config = Config()  # all parameters for project (the base config)
        self.overlay_config = Config()  # all rig specific parameters
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
        self.base_config = Config.from_file(self.base_config_path)
        self.overlay_config = Config.from_file(self.overlay_config_path)
        self.config.merge(self.base_config)
        self.config.merge(self.overlay_config)
    
    def set_config(self, key: str, value):
        value = type(self.config.get_nested(key.split("/")))(value)
        self.config.set_nested(key.split("/"), value)
        self.overlay_config.set_nested(key.split("/"), value, create=True)
        self.overlay_config.save()

    def _init_log(self):
        """Call the LoggerManager get_logger method to initialize logger. Only call once!"""
        return LoggerManager.get_logger(self.config.log)

    def set_parameter(self, key: tuple, value):
        """
        Calls RecursiveNamespace.set_nested on merged config object. Allows config to be set via tuple keys.
        This method also sets the system overlay config and saves it to disk so changes are loaded on restart.

        :param key: a tuple of hashable objects
        :param value: value to set the config entry with
        :return: None
        """
        self.config.set_nested(key, value)
        self.overlay_config.set_nested(key, value, create=True)
        self.logger.info("Setting parameter %s to %s" % (key, value))
        self.logger.info("Saving system overlay to %s" % self.overlay_config_path)
        self.overlay_config.save(self.overlay_config_path)

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
