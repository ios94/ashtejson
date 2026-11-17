"""ashte_rebrand.py — applies the Ashte menu rebrand to ONE unpacked .app folder.
Called from inject.py when inject_dylib == 'Yes'.
Needs libashte.dylib in the repo root (built by the 'Build Ashte Dylib' workflow).
Optional: menu_icon.png (or logo.png) in the repo root for the custom icon.
"""
import os, re, io, sys, base64, struct, zlib, shutil, plistlib, subprocess

DYLIB = "libashte.dylib"
LOAD_PATH = "@executable_path/Frameworks/libashte.dylib"
TITLE = os.environ.get("ASHTE_MENU_TITLE", "Ashte Mod")
ICON = next((p for p in (os.environ.get("ASHTE_MENU_ICON", ""), "menu_icon.png", "logo.png") if p and os.path.isfile(p)), None)

try:
    import lief
except ImportError:
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "lief"])
    import lief
try:
    from PIL import Image
except ImportError:
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "pillow"])
    try:
        from PIL import Image
    except ImportError:
        Image = None

B64 = re.compile(rb'iVBORw0KGgo[A-Za-z0-9+/]{80,}={0,2}')
MACHO = (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')
NAME_VARIANTS = ("Check0ver Team", "CHECK0VER TEAM", "Check0ver team", "Checkover Team")


def available():
    return os.path.isfile(DYLIB)


def _chunk(t, d):
    return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)


def _png_size(blob):
    i = blob.find(b'IHDR')
    if i < 0 or len(blob) < i + 12:
        return None
    w, h = struct.unpack('>II', blob[i + 4:i + 12])
    return (w, h) if (16 <= w <= 700 and 16 <= h <= 700) else None


def _looks_like_mascot(blob):
    try:
        im = Image.open(io.BytesIO(blob)).convert('RGBA')
    except Exception:
        return False
    return len(im.convert('RGB').getcolors(maxcolors=1 << 24) or []) >= 15


def _make_png(target, w, h):
    src = Image.open(ICON).convert('RGBA')
    s = 1.0
    while True:
        nw, nh = max(16, int(w * s)), max(16, int(h * s))
        small = src.resize((nw, nh), Image.LANCZOS)
        for im in (small, small.quantize(colors=128, method=Image.FASTOCTREE)):
            buf = io.BytesIO()
            im.save(buf, 'PNG', optimize=True)
            b = buf.getvalue()
            if len(b) == target:
                return b
            if len(b) + 20 <= target:
                pad = target - len(b) - 20
                return b[:-12] + _chunk(b'tEXt', b'Comment\x00' + b'x' * pad) + b[-12:]
        if nw <= 16:
            return None
        s *= 0.85


def _same_len(old, enc):
    o = old.encode(enc)
    unit = 2 if enc == 'utf-16-le' else 1
    t = TITLE.encode(enc)[:len(o)]
    t += ' '.encode(enc) * ((len(o) - len(t)) // unit)
    return o, t


def _binary_patch(app):
    rep20 = TITLE.encode('utf-8')[:20].ljust(20, b' ')
    for root, _, names in os.walk(app):
        for n in names:
            p = os.path.join(root, n)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            low = n.lower()
            if not (n.endswith(".dylib") or 'igamegod' in low or 'check0ver' in low or 'checkover' in low):
                continue
            with open(p, 'rb') as f:
                data = f.read()
            if data[:4] not in MACHO:
                continue
            new = data
            for pat in (b"Made for iOSGods.com", b"made for iosgods.com"):
                new = new.replace(pat, rep20)
            for variant in NAME_VARIANTS:
                for enc in ('utf-8', 'utf-16-le'):
                    o, r = _same_len(variant, enc)
                    new = new.replace(o, r)
            if ICON and Image:
                for m in set(B64.findall(data)):
                    try:
                        orig = base64.b64decode(m)
                    except Exception:
                        continue
                    wh = _png_size(orig)
                    if wh and _looks_like_mascot(orig):
                        png = _make_png(len(orig), wh[0], wh[1])
                        if png:
                            nb = base64.b64encode(png)
                            if len(nb) == len(m):
                                new = new.replace(m, nb)
            if new != data:
                with open(p, 'wb') as f:
                    f.write(new)
                print(f"  [ashte] patched {os.path.relpath(p, app)}")


def _inject(app):
    with open(os.path.join(app, "Info.plist"), "rb") as f:
        main_exe = plistlib.load(f).get("CFBundleExecutable", "")
    targets = []
    for root, _, names in os.walk(app):
        for n in names:
            if n in ("libashte.dylib", "CydiaSubstrate.dylib", "libsubstitute.dylib"):
                continue
            if n.endswith(".dylib") or n == "iGameGod":
                p = os.path.join(root, n)
                if not os.path.islink(p):
                    targets.append(p)
    main_path = os.path.join(app, main_exe)
    if os.path.isfile(main_path) and main_path not in targets:
        targets.append(main_path)
    for t in targets:
        try:
            fat = lief.MachO.parse(t)
            if fat:
                for b in fat:
                    if any(getattr(l, "name", "") == LOAD_PATH for l in b.libraries):
                        continue
                    b.add_library(LOAD_PATH)
                fat.write(t)
                os.chmod(t, 0o755)
                print(f"  [ashte] injected -> {os.path.relpath(t, app)}")
        except Exception as e:
            print(f"  [ashte] skipped {os.path.relpath(t, app)}: {e}")


def apply(app):
    """app = path to the unpacked Payload/X.app folder."""
    if not available():
        print("  [ashte] libashte.dylib not found in repo root — rebrand skipped (run 'Build Ashte Dylib' once)")
        return False
    _binary_patch(app)
    fw = os.path.join(app, "Frameworks")
    os.makedirs(fw, exist_ok=True)
    shutil.copy2(DYLIB, os.path.join(fw, "libashte.dylib"))
    os.chmod(os.path.join(fw, "libashte.dylib"), 0o755)
    if ICON and Image:
        Image.open(ICON).convert("RGBA").resize((120, 120), Image.LANCZOS).save(os.path.join(app, "ashte_menu_icon.png"), "PNG")
    _inject(app)
    return True
