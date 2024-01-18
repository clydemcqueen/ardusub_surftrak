#!/usr/bin/env python3

"""
Merge logs on TimeUS, producing a single csv file. Fill in (repeat) data as needed.

CTUN is logged at 10Hz (Sub::ten_hz_logging_loop).
stamped_terrain.csv rate comes from the terrain file, but is typically 10Hz.
"""

import os

import pandas as pd

log_dir = os.getenv('LOG_DIR')

terrain_path = os.path.join(log_dir, 'stamped_terrain.csv')
terrain_df = pd.read_csv(terrain_path, index_col='TimeUS')

ctun_path = os.path.join(log_dir, 'ctun.csv')
ctun_df = pd.read_csv(ctun_path, index_col='TimeUS')

merged_path = os.path.join(log_dir, 'merged.csv')
merged_df = pd.merge_ordered(ctun_df, terrain_df, on='TimeUS', fill_method="ffill")

merged_df.to_csv(merged_path)

print('merged.csv written')
