from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try:
    face_test = ImageFont.truetype(font, 24)
except:
    font = 'arial.ttf'

content_dir = root / 'content'
content_dir.mkdir(exist_ok=True)
files = sorted([p.name for p in content_dir.glob('*') if p.is_file()])
if not files:
    files = ['sample_media.mp3']

files = files[:32]

atlas = Image.new('L', (1024, 2048))
draw = ImageDraw.Draw(atlas)
header = []
y = 2

items = [
    ('TITLE', 'Media Machine - File Browser & Transfer', 36),
    ('SUBTITLE', 'Browse content/ and pass files to Switch 2 for client-side playback', 18),
    ('STATUS_READY', 'Status: Ready. Select a media file with D-Pad and press A to pass to Switch 2.', 16),
    ('STATUS_SELECTED', 'Status: File passed to Switch 2 for client-side media playback!', 16),
    ('CONTROLS', 'D-Pad: Navigate | A: Pass File to Switch 2 | X: Clear | B/Minus: Exit', 18)
]

for name, label, size in items:
    try:
        face = ImageFont.truetype(font, size)
    except:
        face = ImageFont.load_default()
    box = draw.textbbox((0, 0), label, font=face)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text((2 - box[0], y - box[1]), label, font=face, fill=255)
    header.append(f'const ivec4 TEXT_{name} = ivec4(2, {y}, {w}, {h});')
    y += h + 8

header.append(f'const int NUM_FILES = {len(files)};')
for i in range(32):
    if i < len(files):
        filename = files[i]
        displayName = filename if len(filename) <= 45 else filename[:42] + '...'
        label = f'{i+1}. {displayName}'
    else:
        label = ''
    try:
        face = ImageFont.truetype(font, 20)
    except:
        face = ImageFont.load_default()
    box = draw.textbbox((0, 0), label, font=face)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text((2 - box[0], y - box[1]), label, font=face, fill=255)
    header.append(f'const ivec4 TEXT_FILE_{i} = ivec4(2, {y}, {w}, {h});')
    y += h + 8

(root / 'assets/text.bin').write_bytes(atlas.tobytes())
(root / 'shaders/text.glsl').write_text('\n'.join(header) + '\n')

im = Image.new('RGBA', (256, 256), (15, 32, 52, 255))
d = ImageDraw.Draw(im)
d.rounded_rectangle((26, 42, 230, 214), radius=22, fill=(28, 60, 90), outline=(80, 220, 240), width=5)
d.rectangle((60, 80, 196, 170), fill=(40, 90, 130), outline=(120, 240, 255), width=3)
d.polygon([(110, 105), (110, 145), (150, 125)], fill=(120, 255, 220))
im.save(root / 'assets/icon.png')
