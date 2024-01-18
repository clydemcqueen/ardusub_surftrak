#!/usr/bin/env python3

import os

import matplotlib

# Set backend before importing matplotlib.pyplot
matplotlib.use('pdf')

import matplotlib.pyplot as plt
import pandas as pd


def graph_sitl(log_dir):
    df = pd.read_csv(os.path.join(log_dir, 'merged.csv'))

    # Rebase timestamp to start at 0
    start = df['timestamp'][0]
    df['timestamp'] = df['timestamp'].add(-start)

    # Convert some fields from cm to m
    df['rf'] = df['rf_cm'] * 0.01
    df['sub'] = df['sub_cm'] * 0.01
    df['terrain'] = df['terrain_cm'] * 0.01

    # Create 1 figure with 3 subplots
    fig, (ax_alt, ax_rf, ax_crt) = plt.subplots(3)

    # Add CTUN fields
    ax_alt.plot('timestamp', 'DAlt', data=df, label='CTUN.DAlt')
    ax_alt.plot('timestamp', 'Alt', data=df, label='CTUN.Alt')
    ax_alt.plot('timestamp', 'TAlt', data=df, label='CTUN.TAlt')

    ax_rf.plot('timestamp', 'DSAlt', data=df, label='CTUN.DSAlt')
    ax_rf.plot('timestamp', 'SAlt', data=df, label='CTUN.SAlt')

    ax_crt.plot('timestamp', 'DCRt', data=df, label='CTUN.DCRt')
    ax_crt.plot('timestamp', 'CRt', data=df, label='CTUN.CRt')

    # Add stamped_terrain.csv fields
    ax_alt.plot('timestamp', 'sub', data=df, label='Older sub pos')
    ax_alt.plot('timestamp', 'terrain', data=df, label='Older terrain pos')

    ax_rf.plot('timestamp', 'rf', data=df, label='Injected rangefinder')

    ax_alt.legend()
    ax_rf.legend()
    ax_crt.legend()

    ax_alt.grid(axis='x')
    ax_rf.grid(axis='x')
    ax_crt.grid(axis='x')

    def rf_error(row):
        return abs(row['SAlt'] - row['DSAlt'])
    df['rf_error'] = df.apply(rf_error, axis=1)

    cr_var = df['CRt'].var()
    rf_error_sum = df['rf_error'].sum()

    plt.suptitle(f'{log_dir}, CRt var: {cr_var :.2f}, RF error sum: {rf_error_sum :.3f}')
    plt.savefig(os.path.join(log_dir, 'merged.pdf'))


# Set defaults
plt.rcParams['figure.figsize'] = [8.5, 11.0]
plt.rcParams['font.size'] = 9
plt.rcParams['lines.linewidth'] = 0.5

log_dir = os.getenv('LOG_DIR')

graph_sitl(log_dir)
