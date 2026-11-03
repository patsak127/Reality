"""Demo producer for SPEC.md section 8 (not part of Reality; untrusted; Python standard library only).

Renders 4 reference frames (256x160, 8-bit RGB) with integer arithmetic only, makes a 128x80
version by 2x2 averaging, upscales it three ways (nearest, bilinear, stylised), and writes into
the folder given as the first argument (default: ./data):
  frames/*.ppm        the reference and upscaled frames
  out_<method>.tsv    one row per pixel per frame for one method: ref and out RGB levels and the
                      edge flags, which are computed HERE, outside the checker
Nothing uses floating point.
"""
import hashlib, pathlib, sys

W, H, FRAMES = 256, 160, 4
here = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "data"
(here / "frames").mkdir(parents=True, exist_ok=True)


def render(t):
    cx, cy, r = 70 + 12 * t, 70, 22          # sun disc moves 12 px right per frame
    img = []
    for y in range(H):
        row = []
        for x in range(W):
            p = (40 + (180 * y) // H, 110 + (60 * y) // H, 150 - (90 * y) // H)   # graded sky
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                p = (250, 170, 60)                                             # sun
            hill = y >= 120 - (x * (W - x)) // 640
            if hill:
                p = (24, 30, 46)                                               # hill
            elif y == 30 + x // 8 or y == 44 + x // 8:
                p = (12, 12, 18)                                               # 1 px power lines
            row.append(p)
        img.append(row)
    return img


def down2(img):
    return [[tuple((img[2*y][2*x][c] + img[2*y+1][2*x][c] + img[2*y][2*x+1][c] + img[2*y+1][2*x+1][c] + 2) // 4
                   for c in range(3)) for x in range(W // 2)] for y in range(H // 2)]


def up_nearest(lo):
    return [[lo[y // 2][x // 2] for x in range(W)] for y in range(H)]


def up_bilinear(lo):
    h, w = len(lo), len(lo[0])
    def nb(i, j, n):            # neighbour index for output index j at low index i, clipped
        return min(max(i + (1 if j % 2 else -1), 0), n - 1)
    out = []
    for y in range(H):
        iy = y // 2; ny = nb(iy, y, h)
        row = []
        for x in range(W):
            ix = x // 2; nx = nb(ix, x, w)
            row.append(tuple((9 * lo[iy][ix][c] + 3 * lo[iy][nx][c] + 3 * lo[ny][ix][c] + lo[ny][nx][c] + 8) // 16
                             for c in range(3)))
        out.append(row)
    return out


def up_stylised(lo):
    out = []
    for row in up_bilinear(lo):
        new = []
        for (r, g, b) in row:
            luma = (299 * r + 587 * g + 114 * b + 500) // 1000
            px = [luma + ((v - luma) * 5) // 4 + s for v, s in zip((r, g, b), (8, 0, -8))]   # saturation 5/4, warm shift
            new.append(tuple(min(max(v, 0), 255) for v in px))
        out.append(new)
    return out


def edges(img):
    l = [[299 * p[0] + 587 * p[1] + 114 * p[2] for p in row] for row in img]       # luma x1000
    return [[1 if max(abs(l[y][x] - l[y][x-1]) if x else 0, abs(l[y][x] - l[y-1][x]) if y else 0) >= 40_000 else 0
             for x in range(W)] for y in range(H)]                                 # step >= 40 levels


def ppm(path, img):
    path.write_bytes(f"P6 {W} {H} 255\n".encode() + bytes(v for row in img for p in row for v in p))


methods = {"nearest": up_nearest, "bilinear": up_bilinear, "stylised": up_stylised}
rows = {m: ["frame\tref_r\tref_g\tref_b\tout_r\tout_g\tout_b\tref_edge\tout_edge"] for m in methods}
for t in range(FRAMES):
    ref = render(t); ppm(here / "frames" / f"ref_f{t}.ppm", ref)
    re = edges(ref); lo = down2(ref)
    for m, f in methods.items():
        out = f(lo); ppm(here / "frames" / f"{m}_f{t}.ppm", out)
        oe = edges(out)
        for y in range(H):
            for x in range(W):
                a, b = ref[y][x], out[y][x]
                rows[m].append(f"f{t}\t{a[0]}\t{a[1]}\t{a[2]}\t{b[0]}\t{b[1]}\t{b[2]}\t{re[y][x]}\t{oe[y][x]}")
for m in methods:
    data = ("\n".join(rows[m]) + "\n").encode()
    (here / f"out_{m}.tsv").write_bytes(data)
    print(f"out_{m}.tsv", len(rows[m]) - 1, "rows sha256:" + hashlib.sha256(data).hexdigest())
