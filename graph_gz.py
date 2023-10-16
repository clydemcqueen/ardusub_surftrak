#!/usr/bin/env python3

import os

import matplotlib

# Set backend before importing matplotlib.pyplot
matplotlib.use('pdf')

import matplotlib.pyplot as plt
import pandas as pd


def graph_gz(csv_path, pdf_path):
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


# Set defaults
plt.rcParams['figure.figsize'] = [8.5, 11.0]
plt.rcParams['font.size'] = 9
plt.rcParams['lines.linewidth'] = 0.5

log_dir = os.getenv('LOG_DIR')

graph_gz(os.path.join(log_dir, 'ctun.csv'), os.path.join(log_dir, 'ctun.pdf'))
