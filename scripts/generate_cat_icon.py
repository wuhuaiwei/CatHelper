"""Rebuild cat.ico using only Python's standard library (no Tk/Pillow).

Rasterize the Pet canvas geometry at 256 x 256 with 3 x 3 sampling,
box-filter to each size, encode RGBA PNGs, then assemble an ICO directory.
"""
from pathlib import Path
import struct
import zlib

SIZES = (16, 24, 32, 48, 64, 128, 256)


def rgb(color):
    return tuple(bytes.fromhex(color.lstrip('#'))) + (255,)


def polygon(x, y, points):
    inside = False
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def ellipse(x, y, bounds):
    a, b, c, d = bounds
    return ((x-(a+c)/2)/((c-a)/2))**2 + ((y-(b+d)/2)/((d-b)/2))**2 <= 1


def line(x, y, a, b, radius=1):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return (x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2 <= radius**2


def rasterize():
    size = 768
    pixels = bytearray(size*size*4)
    purple, outline = rgb('#C8B8FA'), rgb('#8D79C3')
    for py in range(size):
        y = (py+.5)*100/size
        for px in range(size):
            x = (px+.5)*100/size-3
            color = (0, 0, 0, 0)
            if ellipse(x, y, (17, 85, 81, 96)):
                color = rgb('#E7E0F5')
            for points in (((18, 41), (18, 11), (39, 27)), ((57, 27), (77, 11), (79, 42))):
                if polygon(x, y, points):
                    color = purple
                if any(line(x, y, a, b) for a, b in zip(points, points[1:]+points[:1])):
                    color = outline
            if ellipse(x, y, (15, 24, 82, 90)):
                color = outline
            if ellipse(x, y, (17, 26, 80, 88)):
                color = rgb('#DDD2FF')
            if any(ellipse(x, y, bounds) for bounds in ((26, 59, 39, 67), (60, 59, 73, 67))):
                color = rgb('#F3B8D2')
            if any(ellipse(x, y, bounds) for bounds in ((33, 47, 39, 55), (58, 47, 64, 55))):
                color = rgb('#493E64')
            if line(x, y, (45, 62), (49, 65)) or line(x, y, (49, 65), (53, 62)):
                color = rgb('#493E64')
            offset = (py*size+px)*4
            pixels[offset:offset+4] = bytes(color)
    return pixels


def downsample(source, size):
    factor = 768//size
    result = bytearray()
    for y in range(size):
        result.append(0)  # PNG filter: none
        for x in range(size):
            sums = [0, 0, 0, 0]
            for sy in range(y*factor, (y+1)*factor):
                for sx in range(x*factor, (x+1)*factor):
                    offset = (sy*768+sx)*4
                    alpha = source[offset+3]
                    for c in range(3):
                        sums[c] += source[offset+c]*alpha
                    sums[3] += alpha
            alpha = sums[3]
            result.extend([round(sums[c]/alpha) if alpha else 0 for c in range(3)])
            result.append(round(alpha/(factor*factor)))
    return result


def chunk(kind, payload):
    return struct.pack('>I', len(payload))+kind+payload+struct.pack('>I', zlib.crc32(kind+payload))


def png(source, size):
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(downsample(source, size), 9)) + chunk(b'IEND', b''))


def main():
    source = rasterize()
    payloads = [png(source, size) for size in SIZES]
    offset = 6+16*len(SIZES)
    directory = bytearray(struct.pack('<HHH', 0, 1, len(SIZES)))
    for size, payload in zip(SIZES, payloads):
        directory.extend(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)
    path = Path(__file__).resolve().parent.parent/'assets'/'cat.ico'
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(directory+b''.join(payloads))
    print(path)


if __name__ == '__main__':
    main()
