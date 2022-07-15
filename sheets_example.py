import time

from lib.google_sheets import read_google_sheet_rows, write_occupied_values

if __name__ == '__main__':
    row_values = read_google_sheet_rows()
    for row in row_values:
        print(row)

    time.sleep(3)

    write_occupied_values([True, True, True, True, True, True])
    time.sleep(5)
    write_occupied_values([False, False, False, False, False, False])
    time.sleep(5)

    write_occupied_values([row.occupied for row in row_values])


