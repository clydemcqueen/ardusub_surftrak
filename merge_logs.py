#!/usr/bin/env python3

import pandas as pd

# Merge on TimeUS, which is time-since-boot in microseconds

terrain_df = pd.read_csv('stamped_terrain.csv', index_col='TimeUS')
# print(terrain_df)

# mavlogdump.py --types CTUN --format csv 00000067.BIN > ctun67.csv
ctun_df = pd.read_csv('ctun.csv', index_col='TimeUS')
# print(ctun_df)

# Merge the log files, filling in data (repeating) as needed
merged_df = pd.merge_ordered(ctun_df, terrain_df, on='TimeUS', fill_method="ffill")
# print(merged_df)

merged_df.to_csv('merged.csv')

print('merged.csv written')
