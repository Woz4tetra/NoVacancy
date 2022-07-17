import time
import asyncio
import threading
from novacancy.google_sheets import read_database, write_occupied_values, read_devices_config, read_groups_config
from lib.recursive_namespace import RecursiveNamespace


class Behaviors:
    def __init__(self, logger, config: RecursiveNamespace, tunnel_factory):
        self.logger = logger
        self.tunnel_factory = tunnel_factory
        self.config = config

        self.occupancy_states = {}
        self.bigsign_states = {}

        self.prev_occupancy_row = []

        self.rows = []
        self.rows_lock = threading.Lock()
        self.db_poll_task = threading.Thread(target=self.poll_db)
        self.db_poll_task.daemon = True
        self.db_poll_task.start()

    def poll_db(self):
        while True:
            with self.rows_lock:
                try:
                    self.rows = read_database()
                    time.sleep(1.5)
                    self.update_group_config(read_groups_config())
                    time.sleep(1.5)
                    self.update_devices_config(read_devices_config())
                    time.sleep(1.5)
                except BaseException as e:
                    self.logger.error(e, exc_info=True)
            time.sleep(3.0)
    
    def update_group_config(self, new_group_config: RecursiveNamespace):
        if self.config.groups != new_group_config:
            self.logger.info("Device group config updated: %s" % str(new_group_config.to_dict()))
        self.config.groups = new_group_config

    def update_devices_config(self, new_devices_config: RecursiveNamespace):
        if self.config.devices != new_devices_config:
            self.logger.info("Device config updated: %s" % str(new_devices_config.to_dict()))
        self.config.devices = new_devices_config

    async def poll_occupancy(self):
        while True:
            with self.rows_lock:
                board_ids = [str(row.id) for row in self.rows]
                occupancies = [str(row.occupied) for row in self.rows]

            for tunnel in self.tunnel_factory.iter_tunnels():
                board_id = tunnel.get_board_id()
                occupancy = tunnel.get_occupancy()
                ip_address = tunnel.address[0]

                if tunnel.is_stale():
                    self.logger.info("Board ID %s (%s) is stale! Heartbeat stopped." % (board_id, ip_address))
                    continue
            
                if not tunnel.is_occupancy_device():
                    continue

                if board_id not in self.occupancy_states:
                    self.occupancy_states[board_id] = not occupancy
                if occupancy != self.occupancy_states[board_id]:
                    self.logger.info("Board ID %s (%s) is %s" % (board_id, ip_address, "occupied" if occupancy else "vacant"))
                    if occupancy:
                        tunnel.set_led("occupied")
                    else:
                        tunnel.set_led("vacant")
                self.occupancy_states[board_id] = occupancy

                if board_id in board_ids:
                    db_index = board_ids.index(board_id)
                    occupancies[db_index] = occupancy
                else:
                    self.logger.warn("Board ID %s is not in the database. Not updating row. Available IDs: %s" % (board_id, board_ids))
                self.update_groups(board_id)

            if occupancies != self.prev_occupancy_row:
                try:
                    write_occupied_values(occupancies)
                except BaseException as e:
                    self.logger.error(e, exc_info=True)
                self.prev_occupancy_row = occupancies
            await asyncio.sleep(2.0)

    def get_tunnel(self, board_id):
        for tunnel in self.tunnel_factory.iter_tunnels():
            if board_id == tunnel.board_id:
                return tunnel
        return None

    def get_group_name(self, board_id):
        for group_name, values in self.config.groups.items():
            if board_id in values.devices:
                return group_name
        return None

    def get_board_bigsign(self, board_id):
        for values in self.config.groups.values():
            if board_id in values.devices:
                return values.bigsign
        return None

    def get_group_ids(self, group_name):
        if group_name in self.config.groups:
            return self.config.groups[group_name].devices
        else:
            return None

    def update_groups(self, board_id):
        if board_id in self.bigsign_states:
            self.logger.warn("Board %s is a big sign. Not going to check its group." % board_id)
            return  # the polled board is a big sign. No occupancy data
        with self.rows_lock:
            group_name = self.get_group_name(board_id)
            if group_name is None:
                self.logger.warn("Board %s is not associated with a group" % board_id)
                return
            bigsign_id = self.get_board_bigsign(board_id)
            if bigsign_id is None:
                self.logger.warn("Board %s is not associated with a big sign" % board_id)
                return
            if bigsign_id not in self.bigsign_states:
                self.bigsign_states[bigsign_id] = False

            group_ids = self.get_group_ids(group_name)
            if group_ids is None:
                self.logger.warn("Group name %s is not registered" % group_name)
                return
            for bid in group_ids:
                if bid not in self.occupancy_states:
                    self.logger.warn("Board %s is not connected. State not registered" % bid)
                    return

            states = [self.occupancy_states[bid] for bid in group_ids]
            bigsign_state = all(states)

            if bigsign_state != self.bigsign_states[bigsign_id]:
                tunnel = self.get_tunnel(bigsign_id)
                if tunnel is not None:
                    tunnel.set_bigsign(bigsign_state)
                else:
                    self.logger.warn("%s doesn't map to a connected board!" % bigsign_id)
                self.logger.info("Setting %s big sign to %sVacancy" % (bigsign_id, "No " if bigsign_state else ""))

            self.bigsign_states[bigsign_id] = bigsign_state
