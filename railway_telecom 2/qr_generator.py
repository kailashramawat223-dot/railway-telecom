"""
qr_generator.py
Pure-Python QR Code generator (Version 1–10, ECC Level M)
No external libraries beyond Pillow.
"""
from PIL import Image, ImageDraw
import hashlib, struct

# ── Reed-Solomon GF(256) with primitive poly x^8+x^4+x^3+x^2+1 ──────────────
_PRIM = 0x11d

def _gf_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi: a ^= (_PRIM & 0xFF)
        b >>= 1
    return p

# Build exp/log tables
_EXP = [0]*512
_LOG = [0]*256
x = 1
for i in range(255):
    _EXP[i] = x
    _LOG[x] = i
    x = _gf_mul(x, 2)
for i in range(255, 512):
    _EXP[i] = _EXP[i-255]

def _gf_inv(a):  return _EXP[255 - _LOG[a]] if a else 0
def _gf_div(a,b): return _gf_mul(a, _gf_inv(b))
def _poly_mul(p, q):
    r = [0]*(len(p)+len(q)-1)
    for i,a in enumerate(p):
        for j,b in enumerate(q):
            r[i+j] ^= _gf_mul(a,b)
    return r

def _gen_poly(n):
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _EXP[i]])
    return g

def _rs_encode(data, n_ecc):
    gen = _gen_poly(n_ecc)
    msg = list(data) + [0]*n_ecc
    for i in range(len(data)):
        if msg[i]:
            coef = msg[i]
            for j in range(1, len(gen)):
                msg[i+j] ^= _gf_mul(gen[j], coef)
    return msg[len(data):]

# ── QR Code data (hardcoded tables for v1-v10, ECC M) ────────────────────────
# (ec_codewords_per_block, blocks, data_capacity_bytes)
_PARAMS = {
    1: (10, 1, 16), 2: (16, 1, 28), 3: (26, 2, 44),
    4: (18, 2, 64), 5: (24, 2, 86), 6: (16, 4, 108),
    7: (18, 4, 124),8: (22, 4, 154),9: (22, 5, 182),
   10: (26, 5, 216),
}

_ALIGNMENT = {1:[],2:[(18,18)],3:[(22,22)],4:[(26,26)],5:[(30,30)],
              6:[(34,34)],7:[(6,22,38),(6,22,38)],8:[(6,24,42),(6,24,42)],
              9:[(6,26,46),(6,26,46)],10:[(6,28,50),(6,28,50)]}

_ALIGN_POS = {
    2:[18],3:[22],4:[26],5:[30],6:[34],
    7:[6,22,38],8:[6,24,42],9:[6,26,46],10:[6,28,50]
}

def _find_version(n_bytes):
    for v in range(1,11):
        ec,bl,cap = _PARAMS[v]
        if cap >= n_bytes:
            return v
    raise ValueError("Data too long for version 1-10")

def _encode_byte(text):
    data = text.encode('iso-8859-1')
    n = len(data)
    # Mode indicator (byte=0100), char count (8 bits), data, terminator
    bits = []
    def push(val, length):
        for i in range(length-1,-1,-1): bits.append((val>>i)&1)
    push(0b0100, 4)
    push(n, 8)
    for b in data:
        push(b, 8)
    return bits

def _pad_bits(bits, total_bits):
    bits += [0,0,0,0]  # terminator
    while len(bits) % 8: bits.append(0)
    pads = [0xEC,0x11]
    i = 0
    while len(bits) < total_bits:
        bits += [ (pads[i%2]>>j)&1 for j in range(7,-1,-1) ]
        i+=1
    return bits[:total_bits]

def _bits_to_bytes(bits):
    out = []
    for i in range(0,len(bits),8):
        byte = 0
        for j in range(8): byte = (byte<<1)|bits[i+j]
        out.append(byte)
    return out

def _interleave(blocks):
    result = []
    max_len = max(len(b) for b in blocks)
    for i in range(max_len):
        for b in blocks:
            if i < len(b): result.append(b[i])
    return result

# ── Matrix ────────────────────────────────────────────────────────────────────
def _make_matrix(v):
    size = v*4+17
    mat  = [[None]*size for _ in range(size)]  # None=free, True=dark, False=light

    def set_rect(r,c,pat):
        for dr,row in enumerate(pat):
            for dc,val in enumerate(row):
                if 0<=r+dr<size and 0<=c+dc<size:
                    mat[r+dr][c+dc] = bool(val)

    # Finder patterns
    FP = [[1,1,1,1,1,1,1],
          [1,0,0,0,0,0,1],
          [1,0,1,1,1,0,1],
          [1,0,1,1,1,0,1],
          [1,0,1,1,1,0,1],
          [1,0,0,0,0,0,1],
          [1,1,1,1,1,1,1]]
    set_rect(0,0,FP); set_rect(0,size-7,FP); set_rect(size-7,0,FP)
    # Separators
    for i in range(8):
        mat[7][i]=mat[i][7]=mat[7][size-1-i]=mat[i][size-8]=mat[size-8][i]=mat[size-1-i][7]=False
    # Timing
    for i in range(8,size-8):
        mat[6][i] = mat[i][6] = (i%2==0)
    # Dark module
    mat[size-8][8]=True
    # Alignment
    if v>=2:
        pos=_ALIGN_POS.get(v,[])
        AP=[[1,1,1,1,1],[1,0,0,0,1],[1,0,1,0,1],[1,0,0,0,1],[1,1,1,1,1]]
        for r in pos:
            for c in pos:
                if mat[r-2][c-2] is None: set_rect(r-2,c-2,AP)
    return mat, size

def _apply_data(mat, size, data_bytes):
    mat = [row[:] for row in mat]
    bit_idx = 0
    total   = len(data_bytes)*8
    def next_bit():
        nonlocal bit_idx
        if bit_idx >= total: return 0
        b = (data_bytes[bit_idx//8] >> (7-(bit_idx%8))) & 1
        bit_idx += 1
        return b
    # zig-zag column pairs right-to-left, skipping column 6
    cols = list(range(size-1,-1,-1))
    cols_pairs = []
    i=0
    while i<len(cols):
        c=cols[i]
        if c==6: i+=1; continue
        cols_pairs.append((c,cols[i+1] if i+1<len(cols) else None))
        i+=2
    for (cr,cl) in cols_pairs:
        for r_idx in range(size):
            for c in ([cr,cl] if cl is not None else [cr]):
                if c is None: continue
                r = r_idx if (cr%2!=0 or cr==size-1) else size-1-r_idx
                # simple up/down direction based on pair index parity
                if mat[r][c] is None:
                    mat[r][c] = bool(next_bit())
    return mat

def _mask(mat, size, mask_num):
    mat = [row[:] for row in mat]
    for r in range(size):
        for c in range(size):
            if mat[r][c] is None: continue
            cond = [
                (r+c)%2==0, r%2==0, c%3==0,
                (r+c)%3==0, (r//2+c//3)%2==0,
                (r*c)%2+(r*c)%3==0,
                ((r*c)%2+(r*c)%3)%2==0,
                ((r+c)%2+(r*c)%3)%2==0
            ][mask_num]
            if cond: mat[r][c] = not mat[r][c]
    return mat

def _format_info(ecc_level, mask_num):
    # ECC level M = 00, bits[14:13]
    level_bits = {'L':0b01,'M':0b00,'Q':0b11,'H':0b10}['M']
    data = (level_bits<<3)|mask_num
    rem  = data
    for _ in range(10): rem = ((rem<<1)^(0x537 if rem&0x200 else 0))&0x3FF
    fmt  = ((data<<10)|rem)^0x5412
    return fmt

def _apply_format(mat, size, fmt):
    mat=[row[:] for row in mat]
    # Primary copy: around top-left finder
    primary = [(8,0),(8,1),(8,2),(8,3),(8,4),(8,5),(8,7),(8,8),
               (7,8),(5,8),(4,8),(3,8),(2,8),(1,8),(0,8)]
    # Mirror copy: right side and bottom-left
    mirror_col = [(size-1,8),(size-2,8),(size-3,8),(size-4,8),(size-5,8),
                  (size-6,8),(size-7,8)]
    mirror_row = [(8,size-8),(8,size-7),(8,size-6),(8,size-5),(8,size-4),
                  (8,size-3),(8,size-2),(8,size-1)]
    for i,(r,c) in enumerate(primary):
        bit = bool((fmt>>(14-i))&1)
        if 0<=r<size and 0<=c<size: mat[r][c]=bit
    # Mirror: bits 14..8 go to bottom-left column (7 bits)
    for i in range(7):
        bit = bool((fmt>>(14-i))&1)
        r,c = mirror_col[i]
        if 0<=r<size and 0<=c<size: mat[r][c]=bit
    # Mirror: bits 7..0 go to top-right row (8 bits)
    for i in range(8):
        bit = bool((fmt>>(7-i))&1)
        r,c = mirror_row[i]
        if 0<=r<size and 0<=c<size: mat[r][c]=bit
    return mat

def _count_penalty(mat, size):
    score=0
    # Rule 1: 5+ consecutive same color
    for r in range(size):
        run=1
        for c in range(1,size):
            if mat[r][c]==mat[r][c-1]: run+=1
            else:
                if run>=5: score+=run-2
                run=1
        if run>=5: score+=run-2
    for c in range(size):
        run=1
        for r in range(1,size):
            if mat[r][c]==mat[r-1][c]: run+=1
            else:
                if run>=5: score+=run-2
                run=1
        if run>=5: score+=run-2
    return score

def generate_qr_image(text, fill=(26,39,68), back=(255,255,255), box=10, border=4):
    """Generate a QR code PIL Image for `text`."""
    bits   = _encode_byte(text)
    v      = _find_version(len(text.encode('iso-8859-1'))+3)
    ec,bl,cap = _PARAMS[v]
    total_data_bits = (cap)*8
    bits   = _pad_bits(bits, total_data_bits)
    data_b = _bits_to_bytes(bits)

    # Split into blocks and RS-encode
    block_size = cap//bl
    blocks = [data_b[i*block_size:(i+1)*block_size] for i in range(bl)]
    ecc_blocks = [_rs_encode(b, ec) for b in blocks]
    codewords = _interleave(blocks) + _interleave(ecc_blocks)

    mat, size = _make_matrix(v)
    mat = _apply_data(mat, size, codewords)

    # Pick best mask
    best_mat, best_score = None, float('inf')
    for m in range(8):
        mm = _mask(mat, size, m)
        fmt= _format_info('M', m)
        mm = _apply_format(mm, size, fmt)
        s  = _count_penalty(mm, size)
        if s < best_score:
            best_score=s; best_mat=mm; best_mask=m

    # Fill any None (should not happen but safety)
    for r in range(size):
        for c in range(size):
            if best_mat[r][c] is None: best_mat[r][c]=False

    pixel_size = size + border*2
    img = Image.new('RGB', (pixel_size*box, pixel_size*box), back)
    draw= ImageDraw.Draw(img)
    for r in range(size):
        for c in range(size):
            color = fill if best_mat[r][c] else back
            x0=(border+c)*box; y0=(border+r)*box
            draw.rectangle([x0,y0,x0+box-1,y0+box-1], fill=color)
    return img
