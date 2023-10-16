#!/usr/bin/env python3

"""
Compute PID coefficients per https://en.wikipedia.org/wiki/Ziegler%E2%80%93Nichols_method
"""

from argparse import ArgumentParser


def print_gains(ku, tu, name: str, kpc, kic, kdc):
    print(f'{name :20}{kpc * ku :6.2f}{kic * ku / tu :6.2f}{kdc * ku * tu :6.2f}')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('Ku', type=float, help='ultimate gain Ku')
    parser.add_argument('Tu', type=float, help='oscillation period for Ku in seconds')
    args = parser.parse_args()

    print(f'{"Control type" :20}{"P" :^6}{"I" :^6}{"D" :^6}')
    print_gains(args.Ku, args.Tu, 'Classic', 0.6, 1.2, 0.075)
    print_gains(args.Ku, args.Tu, 'Some overshoot', 0.33, 0.66, 0.11)
    print_gains(args.Ku, args.Tu, 'No overshoot', 0.2, 0.4, 0.066)


if __name__ == '__main__':
    main()
