from sys import exc_info
import time
import asyncio
import threading
from lib.google_sheets import read_google_sheet_rows, write_occupied_values


class Behaviors:
    def __init__(self, logger, device_groups, tunnel_factory):
        self.logger = logger
        self.tunnel_factory = tunnel_factory
        self.device_groups = device_groups

        self.id_to_group = {}
        self.group_states = {}
        self.prev_bigsign_states = {}
        for group_name, values in self.device_groups.items():
            self.group_states[group_name] = {}
            self.prev_bigsign_states[group_name] = False
            for board_id in values.devices:
                self.id_to_group[board_id] = group_name
                self.group_states[group_name][board_id] = False
        
        self.rows = []
        self.rows_lock = threading.Lock()
        self.db_poll_task = threading.Thread(target=self.poll_db)
        self.db_poll_task.daemon = True
        self.db_poll_task.start()

    def poll_db(self):
        while True:
            with self.rows_lock:
                try:
                    self.rows = read_google_sheet_rows()
                except BaseException as e:
                    self.logger.error(e, exc_info=True)
            time.sleep(5.0)

    async def poll_occupancy(self):
        while True:
            with self.rows_lock:
                board_ids = [str(row.id) for row in self.rows]
                occupancies = [str(row.occupied) for row in self.rows]

            for tunnel in self.tunnel_factory.iter_tunnels():
                occupancy = tunnel.get_occupancy()
                board_id = tunnel.get_board_id()
                ip_address = tunnel.address[0]
                if tunnel.is_stale():
                    self.logger.info("Board ID %s (%s) is stale! Heartbeat stopped." % (board_id, ip_address))
                    continue
                else:
                    self.logger.info("Board ID %s (%s) is %s" % (board_id, ip_address, "occupied" if occupancy else "vacant"))
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
        group_name = self.id_to_group[board_id]
        if group_name in self.group_states and board_id in self.group_states[group_name]:
            states = self.group_states[group_name]
            states[board_id] = occupancy

            bigsign_state = all(states.values())
            if bigsign_state != self.prev_bigsign_states[group_name]:
                tunnel = self.get_tunnel(board_id)
                tunnel.set_bigsign(bigsign_state)
                if bigsign_state:
                    tunnel.play_sound("poweron")
                else:
                    tunnel.play_sound("poweroff")

            self.prev_bigsign_states[group_name] = bigsign_state
        else:
            self.logger.warn("Board ID %s is not associated with a group" % board_id)
