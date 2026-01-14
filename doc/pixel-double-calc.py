#!/usr/bin/env python3

import argparse
import sys
from pprint import pprint

parser = argparse.ArgumentParser(
                prog="video-route",
                description='Web page remote for control video processors',
                epilog='')
parser.add_argument('-4', '--uhd', help="Calculate for 4K frame", action='store_true')
parser.add_argument('-r', '--ratio', help="Ignore aspect ratio", action='store_true')
parser.add_argument('size', help="", default=None, nargs=argparse.REMAINDER)
args = parser.parse_args()



if args.size is None or len(args.size) != 2:
    print("add the horizontal and vertical resolution as parameters")
    sys.exit(1)

resolution_in = args.size
resolution_in[0] = int(resolution_in[0])
resolution_in[1] = int(resolution_in[1])
resolution_out = {}

frame_x = 3840 if args.uhd else 1920
frame_y = 2160 if args.uhd else 1080

scale_x=1
while resolution_in[0] * (scale_x+1) <= frame_x:
    scale_x+=1

scale_y=1
while resolution_in[1] * (scale_y+1) <= frame_y:
    scale_y+=1

if not args.ratio:
    if scale_x > scale_y:
        scale_x = scale_y
    if scale_y > scale_x:
        scale_y = scale_x

resolution_out[0] = resolution_in[0] * scale_x
resolution_out[1] = resolution_in[1] * scale_y


print(f'{resolution_in[0]} x {resolution_in[1]} to {resolution_out[0]} x {resolution_out[1]} [{scale_x}:{scale_y}]')
print(f'Offset from edge {int((frame_x-resolution_out[0])/2)} x {int((frame_y-resolution_out[1])/2)}')
