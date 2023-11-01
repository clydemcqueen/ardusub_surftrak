#!/usr/bin/env python3

import os

import pandas as pd

log_dir = os.getenv('LOG_DIR')
terrain_path = os.path.join(log_dir, 'stamped_terrain.csv')
ctun_path = os.path.join(log_dir, 'ctun.csv')
merged_path = os.path.join(log_dir, 'merged.csv')

# Merge on TimeUS, which is time-since-boot in microseconds

terrain_df = pd.read_csv(terrain_path, index_col='TimeUS')
# print(terrain_df)

# mavlogdump.py --types CTUN --format csv 00000067.BIN > ctun67.csv
ctun_df = pd.read_csv(ctun_path, index_col='TimeUS')
# print(ctun_df)

# Merge the log files, filling in data (repeating) as needed
merged_df = pd.merge_ordered(ctun_df, terrain_df, on='TimeUS', fill_method="ffill")
# print(merged_df)

merged_df.to_csv(merged_path)

print('merged.csv written')
