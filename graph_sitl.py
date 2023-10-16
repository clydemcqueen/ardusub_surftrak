#!/usr/bin/env python3

import os

import matplotlib

# Set backend before importing matplotlib.pyplot
matplotlib.use('pdf')

import matplotlib.pyplot as plt
import pandas as pd


def graph_sitl(csv_path, pdf_path):
    df = pd.read_csv(csv_path)

    # Rebase timestamp to start at 0
    start = df['timestamp'][0]
    df['timestamp'] = df['timestamp'].add(-start)

    # Create 1 figure with 3 subplots
    fig, (ax_alt, ax_rf, ax_crt) = plt.subplots(3)

    # Add CTUN fields
    ax_alt.plot('timestamp', 'DAlt', data=df, label='CTUN target z')
    ax_alt.plot('timestamp', 'Alt', data=df, label='CTUN EKF z')
    ax_alt.plot('timestamp', 'BAlt', data=df, label='CTUN barometer z')

    ax_rf.plot('timestamp', 'DSAlt', data=df, label='CTUN target rangefinder')
    ax_rf.plot('timestamp', 'SAlt', data=df, label='CTUN rangefinder')

    ax_crt.plot('timestamp', 'DCRt', data=df, label='CTUN target climb rate')
    ax_crt.plot('timestamp', 'CRt', data=df, label='CTUN climb rate')

    # Add stamped_terrain.csv fields
    ax_alt.plot('timestamp', 'sub_z', data=df, label='Injection-time z')
    ax_alt.plot('timestamp', 'terrain_z', data=df, label='Terrain z')

    ax_rf.plot('timestamp', 'rf', data=df, label='Injected rangefinder')

    ax_alt.legend()
    ax_rf.legend()
    ax_crt.legend()

    ax_alt.grid(axis='x')
    ax_rf.grid(axis='x')
    ax_crt.grid(axis='x')

    plt.savefig(pdf_path)


# Set defaults
plt.rcParams['figure.figsize'] = [8.5, 11.0]
plt.rcParams['font.size'] = 9
plt.rcParams['lines.linewidth'] = 0.5

log_dir = os.getenv('LOG_DIR')

graph_sitl(os.path.join(log_dir, 'merged.csv'), os.path.join(log_dir, 'merged.pdf'))
