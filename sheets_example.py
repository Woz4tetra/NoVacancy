import time
from pprint import pprint

from novacancy.google_sheets import read_database, write_occupied_values, read_groups_config, read_devices_config

def write_all_test():
    row_values = read_database()
    for row in row_values:
        print(row)

    time.sleep(3)

    write_occupied_values([True, True, True, True, True, True])
    time.sleep(5)
    write_occupied_values([False, False, False, False, False, False])
    time.sleep(5)

    write_occupied_values([row.occupied for row in row_values])




if __name__ == '__main__':
    # write_all_test()
    pprint(read_groups_config().to_dict())
    pprint(read_devices_config().to_dict())
