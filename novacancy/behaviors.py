import time
import asyncio
import threading
from novacancy.google_sheets import read_database, write_occupied_values, read_devices_config, read_groups_config
from lib.recursive_namespace import RecursiveNamespace


class Behaviors:
    def __init__(self, logger, device_groups: RecursiveNamespace, device_config: RecursiveNamespace, tunnel_factory):
        self.logger = logger
        self.tunnel_factory = tunnel_factory
        self.device_groups = device_groups
        self.device_config = device_config

        self.occupancy_states = {}
        self.id_to_group = {}
        self.id_to_bigsign = {}
        self.group_states = {}
        self.prev_bigsign_states = {}
        self.create_group_states()

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
                    self.update_group_config(read_groups_config())
                    self.update_devices_config(read_devices_config())
                except BaseException as e:
                    self.logger.error(e, exc_info=True)
            time.sleep(5.0)
    
    def update_group_config(self, new_group_config: RecursiveNamespace):
        if self.device_groups != new_group_config:
            self.device_groups.merge(new_group_config)
            self.create_group_states()

    def update_devices_config(self, new_devices_config: RecursiveNamespace):
        self.device_config.merge(new_devices_config)

    def create_group_states(self):
        self.id_to_group = {}
        self.group_states = {}
        self.id_to_bigsign = {}
        for group_name, values in self.device_groups.items():
            self.group_states[group_name] = {}
            if values.bigsign not in self.prev_bigsign_states:
                self.prev_bigsign_states[values.bigsign] = False
            for board_id in values.devices:
                self.id_to_group[board_id] = group_name
                self.id_to_bigsign[board_id] = values.bigsign
                self.group_states[group_name][board_id] = False

    async def poll_occupancy(self):
        while True:
            with self.rows_lock:
                board_ids = [str(row.id) for row in self.rows]
                occupancies = [str(row.occupied) for row in self.rows]

            for tunnel in self.tunnel_factory.iter_tunnels():
                if tunnel.is_stale():
                    self.logger.info("Board ID %s (%s) is stale! Heartbeat stopped." % (board_id, ip_address))
                    continue

                occupancy = tunnel.get_occupancy()
                board_id = tunnel.get_board_id()
                ip_address = tunnel.address[0]
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
                self.update_groups(board_id, occupancy)

            write_occupied_values(occupancies)
            await asyncio.sleep(1.0)

    def get_tunnel(self, board_id):
        for tunnel in self.tunnel_factory.iter_tunnels():
            if board_id == tunnel.board_id:
                return tunnel
        return None

    def update_groups(self, board_id, occupancy):
        with self.rows_lock:
            group_name = self.id_to_group[board_id]
            bigsign_id = self.id_to_bigsign[board_id]
            if group_name in self.group_states and board_id in self.group_states[group_name]:
                states = self.group_states[group_name]
                states[board_id] = occupancy

                bigsign_state = all(states.values())
                if bigsign_state != self.prev_bigsign_states[bigsign_id]:
                    tunnel = self.get_tunnel(bigsign_id)
                    if tunnel is not None:
                        tunnel.set_bigsign(bigsign_state)
                    else:
                        self.logger.warn("%s doesn't map to a connected board!" % bigsign_id)
                    self.logger.info("Setting %s big sign to %sVacancy" % (bigsign_id, "No " if bigsign_state else ""))

                self.prev_bigsign_states[bigsign_id] = bigsign_state
            else:
                self.logger.warn("Board ID %s is not associated with a group" % board_id)
