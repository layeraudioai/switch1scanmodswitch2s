from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
import struct
import json

root = Path(__file__).resolve().parent
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try:
    face_test = ImageFont.truetype(font, 24)
except:
    font = 'arial.ttf'

content_dir = root / 'content'
content_dir.mkdir(exist_ok=True)

# Supported audio extensions
audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a', '.wma', '.opus', '.m4b'}
files = sorted([p.name for p in content_dir.glob('*') if p.is_file() and (p.suffix.lower() in audio_extensions or not p.suffix)])
if not files:
    # Fallback to any file or sample_media.mp3
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
    ('STATUS_READY', 'Status: Ready. Select a media file with D-Pad and press A to pass & play.', 16),
    ('STATUS_SELECTED', 'Status: File passed to Switch 2 & playing audio preview!', 16),
    ('CONTROLS', 'D-Pad: Navigate | A: Pass File & Play Audio | X: Clear | B/Minus: Exit', 18)
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

# Generate or decode audio effects for up to 31 files
audio_effects = {}
audio_dir = root / 'assets'
audio_dir.mkdir(exist_ok=True)

try:
    from pydub import AudioSegment
    has_pydub = True
except Exception:
    has_pydub = False

pentatonic = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99, 880.00]

for i in range(min(len(files), 31)):
    filename = files[i]
    filepath = content_dir / filename
    pcm_data = None
    
    if has_pydub and filepath.is_file() and filepath.stat().st_size > 0:
        try:
            # Decode any audio format (.mp3, .wav, .flac, .ogg, .aac, .m4a, .opus, etc.)
            audio = AudioSegment.from_file(str(filepath))
            audio = audio.set_frame_rate(48000).set_channels(2).set_sample_width(2)
            raw_data = audio.raw_data
            if len(raw_data) > 131072:
                raw_data = raw_data[:131072]
            remainder = len(raw_data) % 4
            if remainder != 0:
                raw_data = raw_data[:-remainder]
            if len(raw_data) > 0:
                pcm_data = raw_data
        except Exception as e:
            print(f"Notice: Could not decode {filename} with pydub ({e}), falling back to synthesized tone.")

    if pcm_data is None:
        # Fallback synthesized tone
        freq = pentatonic[i % len(pentatonic)] * (1.0 + (i // len(pentatonic)) * 0.5)
        rate = 48000
        duration = 0.3
        frames = int(rate * duration)
        pcm_buf = bytearray()
        for f_idx in range(frames):
            t = f_idx / rate
            attack = min(1.0, t / 0.005)
            envelope = attack * math.pow(1.0 - (t / duration), 1.5)
            val = math.sin(2.0 * math.pi * freq * t) + 0.25 * math.sin(4.0 * math.pi * freq * t)
            sample = int(32767 * 0.2 * envelope * val)
            sample = max(-32768, min(32767, sample))
            pcm_buf.extend(struct.pack('<hh', sample, sample))
        pcm_data = bytes(pcm_buf)

    pcm_path = audio_dir / f'audio_{i+1}.pcm'
    pcm_path.write_bytes(pcm_data)
    audio_effects[str(i+1)] = f'assets/audio_{i+1}.pcm'

# Update app.json with audio configuration
app_json_path = root / 'app.json'
app_data = json.loads(app_json_path.read_text())
app_data['audio'] = {
    'sampleRate': 48000,
    'channels': 2,
    'format': 's16le',
    'effects': audio_effects
}
app_json_path.write_text(json.dumps(app_data, indent=2) + '\n')
