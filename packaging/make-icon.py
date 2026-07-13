"""Regenerate the app icon master (packaging/icon.png). Requires macOS + pyobjc.

    python packaging/make-icon.py
    # then rebuild icon.icns:
    #   mkdir icon.iconset && for each size: sips -z <px> <px> packaging/icon.png ...
    #   iconutil -c icns icon.iconset -o packaging/icon.icns

A dark squircle with a 2×2 grid of the pane palette (blue/orange/red/green) —
the quad layout, which is what the app arranges.
"""
import os
import Quartz
from Quartz import (CGColorSpaceCreateDeviceRGB, CGBitmapContextCreate,
    kCGImageAlphaPremultipliedLast, CGPathCreateWithRoundedRect, CGRectMake,
    CGContextAddPath, CGContextSetRGBFillColor, CGContextFillPath,
    CGBitmapContextCreateImage, CGImageDestinationCreateWithURL,
    CGImageDestinationAddImage, CGImageDestinationFinalize)
from CoreFoundation import CFURLCreateWithFileSystemPath, kCFURLPOSIXPathStyle
W = H = 1024
ctx = CGBitmapContextCreate(None, W, H, 8, 0, CGColorSpaceCreateDeviceRGB(), kCGImageAlphaPremultipliedLast)
def rrect(x, y, w, h, r, rgba):
    CGContextAddPath(ctx, CGPathCreateWithRoundedRect(CGRectMake(x, y, w, h), r, r, None))
    CGContextSetRGBFillColor(ctx, *rgba); CGContextFillPath(ctx)
rrect(80, 80, 864, 864, 210, (0.055, 0.055, 0.086, 1))
colors = [(0.357,0.557,0.937,1),(0.82,0.635,0.31,1),(0.878,0.333,0.373,1),(0.541,0.604,0.31,1)]
gx = gy = 214; gs = 596; gap = 40; cell = (gs - gap) / 2
pos = [(gx,gy+cell+gap),(gx+cell+gap,gy+cell+gap),(gx,gy),(gx+cell+gap,gy)]
for (x, y), c in zip(pos, colors): rrect(x, y, cell, cell, 58, c)
img = CGBitmapContextCreateImage(ctx)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
url = CFURLCreateWithFileSystemPath(None, out, kCFURLPOSIXPathStyle, False)
dest = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
CGImageDestinationAddImage(dest, img, None); CGImageDestinationFinalize(dest)
print("wrote", out)
