#!/usr/bin/env python3

import matplotlib

# Set backend before importing matplotlib.pyplot
matplotlib.use('pdf')

import matplotlib.pyplot as plt
import pandas as pd


def graph_ctun(csv_path, pdf_path):
    df = pd.read_csv(csv_path)

    fig, (ax_alt, ax_rf, ax_crt) = plt.subplots(3)

    df['DAlt'].plot(ax=ax_alt)
    df['Alt'].plot(ax=ax_alt)
    df['BAlt'].plot(ax=ax_alt)

    df['DSAlt'].plot(ax=ax_rf)
    df['SAlt'].plot(ax=ax_rf)

    df['DCRt'].plot(ax=ax_crt)
    df['CRt'].plot(ax=ax_crt)

    ax_alt.legend(labels=['Target z', 'EKF z', 'Barometer z'])
    ax_rf.legend(labels=['Target rangefinder', 'Rangefinder'])
    ax_crt.legend(labels=['Target climb rate', 'Climb rate'])

    plt.savefig(pdf_path)


def graph_merged(csv_path, pdf_path):
    df = pd.read_csv(csv_path)

    fig, (ax_alt, ax_rf, ax_crt) = plt.subplots(3)

    # From the CTUN log entry in the ArduSub dataflash log
    df['DAlt'].plot(ax=ax_alt)
    df['Alt'].plot(ax=ax_alt)
    df['BAlt'].plot(ax=ax_alt)

    df['DSAlt'].plot(ax=ax_rf)
    df['SAlt'].plot(ax=ax_rf)

    df['DCRt'].plot(ax=ax_crt)
    df['CRt'].plot(ax=ax_crt)

    # From sub.py
    df['sub_z'].plot(ax=ax_alt)
    df['terrain_z'].plot(ax=ax_alt)

    df['rf'].plot(ax=ax_rf)

    ax_alt.legend(labels=['CTUN target z', 'CTUN EKF z', 'CTUN barometer z', 'Injection-time z', 'Terrain z'])
    ax_rf.legend(labels=['CTUN target rangefinder', 'CTUN rangefinder', 'Injected rangefinder'])
    ax_crt.legend(labels=['CTUN target climb rate', 'CTUN climb rate'])

    plt.savefig(pdf_path)


# Set defaults
plt.rcParams['figure.figsize'] = [8.5, 11.0]
plt.rcParams['font.size'] = 9
plt.rcParams['lines.linewidth'] = 0.5

# Generate CTUN graphs (update this list as needed)
graph_ctun('logs/gazebo/auto_alt/ctun.csv', 'logs/gazebo/auto_alt/ctun.pdf')
graph_ctun('logs/gazebo/surftrak/ctun.csv', 'logs/gazebo/surftrak/ctun.pdf')
graph_ctun('logs/gazebo/surftrak_4_1/ctun.csv', 'logs/gazebo/surftrak_4_1/ctun.pdf')

# Generate merged graphs (update this list as needed)
graph_merged('logs/sitl/surftrak/sawtooth/merged.csv', 'logs/sitl/surftrak/sawtooth/merged.pdf')
graph_merged('logs/sitl/surftrak/trapezoid/merged.csv', 'logs/sitl/surftrak/trapezoid/merged.pdf')
graph_merged('logs/sitl/surftrak_4_1/trapezoid/merged.csv', 'logs/sitl/surftrak_4_1/trapezoid/merged.pdf')
