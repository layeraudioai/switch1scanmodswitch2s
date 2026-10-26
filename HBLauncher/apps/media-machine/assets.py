"""Build deterministic audio assets without signal-level processing."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
content_dir = root / 'content'
content_dir.mkdir(exist_ok=True)

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a', '.wma', '.opus', '.m4b'}
VIDEO_EXTENSIONS = {'.mp4', '.m4v', '.mov', '.mkv', '.webm', '.avi', '.3gp', '.ts'}

files = sorted((p for p in content_dir.iterdir() if p.is_file() and
                p.suffix.lower() in AUDIO_EXTENSIONS | VIDEO_EXTENSIONS),
               key=lambda p: p.name.lower())[:31]
video_files = [p for p in files if p.suffix.lower() in VIDEO_EXTENSIONS]

font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try:
    ImageFont.truetype(font, 24)
except OSError:
    font = 'arial.ttf'

atlas = Image.new('L', (1024, 2048))
draw = ImageDraw.Draw(atlas)
header = []
y = 2
items = [
    ('TITLE', 'Media Machine - Video and Audio', 36),
    ('SUBTITLE', 'Select with Up/Down; A plays video or audio', 18),
    ('STATUS_READY', ('Videos are predecoded to 1920x1080 at 60 fps.' if video_files else
                      'Add video or audio files to content/ to begin.'), 16),
    ('STATUS_SELECTED', 'Playing selected media on Switch 2', 16),
    ('CONTROLS', 'D-Pad: Navigate | A: Play | X: Stop | B/Minus: Exit', 18),
]
for name, label, size in items:
    face = ImageFont.truetype(font, size)
    box = draw.textbbox((0, 0), label, font=face)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text((2 - box[0], y - box[1]), label, font=face, fill=255)
    header.append(f'const ivec4 TEXT_{name} = ivec4(2, {y}, {w}, {h});')
    y += h + 8

ui_files = files or [None]
header.append(f'const int NUM_FILES = {len(ui_files)};')
for i in range(32):
    if i < len(ui_files) and ui_files[i] is None:
        label = 'No supported audio files found'
    elif i < len(ui_files):
        label = f'{i + 1}. {files[i].name}'
        if len(label) > 54:
            label = label[:51] + '...'
    else:
        label = ''
    face = ImageFont.truetype(font, 20)
    box = draw.textbbox((0, 0), label, font=face)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text((2 - box[0], y - box[1]), label, font=face, fill=255)
    header.append(f'const ivec4 TEXT_FILE_{i} = ivec4(2, {y}, {w}, {h});')
    y += h + 8

im = Image.new('RGBA', (256, 256), (15, 32, 52, 255))
d = ImageDraw.Draw(im)
d.rounded_rectangle((26, 42, 230, 214), radius=22, fill=(28, 60, 90), outline=(80, 220, 240), width=5)
d.rectangle((60, 80, 196, 170), fill=(40, 90, 130), outline=(120, 240, 255), width=3)
d.polygon([(110, 105), (110, 145), (150, 125)], fill=(120, 255, 220))
im.save(root / 'assets/icon.png')

if files and not shutil.which('ffmpeg'):
    raise RuntimeError('ffmpeg is required to package audio/video files (install ffmpeg and rebuild)')

atlas_bytes = atlas.tobytes()
video_payload = bytearray()
video_meta = [(0, 0, 0) for _ in files]
video_indices = [i for i, source in enumerate(files) if source.suffix.lower() in VIDEO_EXTENSIONS]
frame_width, frame_height, frame_rate = 1920, 1080, 60
frame_bytes = frame_width * frame_height * 2
pieces_dir = root / 'assets'
pieces_dir.mkdir(exist_ok=True)
video_pieces_manifest = {}

for position, i in enumerate(video_indices):
    source = files[i]
    with tempfile.NamedTemporaryFile(prefix=f'media-machine-vid-{i}-', suffix='.rgb565', dir=pieces_dir, delete=False) as tmp:
        temp_name = tmp.name
    command = [
        'ffmpeg', '-v', 'error', '-i', str(source), '-map', '0:v:0', '-an', '-sn', '-dn',
        '-vf', f'fps={frame_rate},scale={frame_width}:{frame_height}:force_original_aspect_ratio=increase,crop={frame_width}:{frame_height}',
        '-f', 'rawvideo', '-pix_fmt', 'rgb565le', '-y', temp_name,
    ]
    try:
        subprocess.run(command, check=True, timeout=1800)
        decoded_size = Path(temp_name).stat().st_size
        if not decoded_size or decoded_size % frame_bytes:
            raise RuntimeError(f'FFmpeg produced invalid frames for {source.name}')
        frame_count = decoded_size // frame_bytes
        offset = len(atlas_bytes) + len(video_payload)
        piece_paths = {}
        with Path(temp_name).open('rb') as decoded:
            frame0_bytes = decoded.read(frame_bytes)
            video_payload.extend(frame0_bytes)
            p0_path = pieces_dir / f'video_{i}_p0.rgb565'
            p0_path.write_bytes(frame0_bytes)
            piece_paths['0'] = str(p0_path.relative_to(root))
            for f_idx in range(1, frame_count):
                fb = decoded.read(frame_bytes)
                if not fb:
                    break
                p_path = pieces_dir / f'video_{i}_p{f_idx}.rgb565'
                p_path.write_bytes(fb)
                piece_paths[str(f_idx)] = str(p_path.relative_to(root))

        video_meta[i] = (offset, frame_count, frame_rate)
        video_pieces_manifest[str(i)] = {
            'offset': offset,
            'fps': frame_rate,
            'totalFrames': frame_count,
            'pieces': piece_paths
        }
        print(f'Chunked {source.name}: {frame_count} frames into pre-rendered piece files at {frame_width}x{frame_height}')
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Could not process video {source.name}') from exc
    finally:
        Path(temp_name).unlink(missing_ok=True)

if len(atlas_bytes) + len(video_payload) > 7 * 1024 * 1024:
    raise RuntimeError('Packaged video data exceeds the 7 MiB app data limit')

header.append('const ivec3 VIDEO_META[31] = ivec3[31](')
header.append(',\n'.join(f'    ivec3({offset}, {count}, {fps})' for offset, count, fps in video_meta + [(0, 0, 0)] * (31 - len(video_meta))))
header.append(');')
(root / 'assets/text.bin').write_bytes(atlas_bytes + video_payload)
(root / 'shaders/text.glsl').write_text('\n'.join(header) + '\n')
(root / 'assets/video-pieces.json').write_text(json.dumps(video_pieces_manifest, indent=2) + '\n')

audio_files = [p for p in files if p.suffix.lower() in AUDIO_EXTENSIONS]
audio_effects = {}
for i, source in enumerate(files, 1):
    target = audio_dir / f'audio_{i}.pcm' if 'audio_dir' in locals() else (root / f'assets/audio_{i}.pcm')
    if source.suffix.lower() not in AUDIO_EXTENSIONS | VIDEO_EXTENSIONS:
        continue
    with tempfile.NamedTemporaryFile(prefix='media-machine-', suffix='.pcm', dir=root / 'assets', delete=False) as tmp:
        temp_name = tmp.name
    try:
        command = [
            'ffmpeg', '-v', 'error', '-i', str(source), '-map', '0:a:0', '-vn',
            '-acodec', 'pcm_s16le', '-f', 's16le', '-ar', '48000', '-ac', '2', '-y', temp_name,
        ]
        try:
            subprocess.run(command, check=True, timeout=1800)
        except subprocess.CalledProcessError:
            if source.suffix.lower() in VIDEO_EXTENSIONS:
                continue
            raise
        size = Path(temp_name).stat().st_size
        if not size or size % 4:
            if source.suffix.lower() in VIDEO_EXTENSIONS:
                continue
            raise RuntimeError(f'ffmpeg produced invalid stereo PCM for {source.name}')
        Path(temp_name).replace(target)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Could not decode {source.name}') from exc
    finally:
        Path(temp_name).unlink(missing_ok=True)
    audio_effects[str(i)] = f'assets/audio_{i}.pcm'

for stale in (root / 'assets').glob('audio_*.pcm'):
    try:
        if stale.name not in {f'audio_{i}.pcm' for i in range(1, len(files) + 1)}:
            stale.unlink()
    except OSError:
        pass
manifest_path = root / 'app.json'
manifest = json.loads(manifest_path.read_text())
manifest['audio'] = {
    'sampleRate': 48000, 'channels': 2, 'format': 's16le', 'effects': audio_effects,
}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
