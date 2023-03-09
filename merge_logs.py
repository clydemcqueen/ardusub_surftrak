#!/usr/bin/env python3

import pandas as pd
# from telemetry.mavlogparse import Telemetry


# tlog_df = Telemetry.csv_to_df('tlog.csv', timezone='US/Pacific')
# print(tlog_df)


def parser(utc_epoch_seconds):
    return (pd.to_datetime(utc_epoch_seconds, unit='s')
            .tz_localize('utc').tz_convert('US/Pacific'))


terrain_df = pd.read_csv('stamped_terrain.csv', index_col='timestamp', parse_dates=['timestamp'], date_parser=parser)
# print(terrain_df)

# mavlogdump.py --types CTUN --format csv 00000067.BIN > ctun67.csv
ctun_df = pd.read_csv('ctun.csv', index_col='timestamp', parse_dates=['timestamp'], date_parser=parser)
# print(ctun_df)

# Merge the log files, filling in data (repeating) as needed
# merged_df = pd.merge_ordered(tlog_df, terrain_df, on='timestamp', fill_method="ffill")
merged_df = pd.merge_ordered(ctun_df, terrain_df, on='timestamp', fill_method="ffill")
# print(merged_df)

merged_df.to_csv('merged.csv')

print('merged.csv written')