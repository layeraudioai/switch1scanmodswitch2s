from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parent
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
atlas=Image.new('L',(1024,2048));draw=ImageDraw.Draw(atlas);header=[];y=2
items=[
    ('TITLE','Media Player Suite',54),
    ('SUBTITLE','Host-streamed MP3, FLAC, WAV, OPUS, MP4 & WEBM Suite',24),
    ('MP3','[MP3] Audio Track - stream via PC Host / FTP',26),
    ('FLAC','[FLAC] Lossless Audio - stream via PC Host / FTP',26),
    ('WAV','[WAV] Uncompressed Audio - stream via PC Host / FTP',26),
    ('OPUS','[OPUS] High-Efficiency Audio - stream via PC Host / FTP',26),
    ('MP4','[MP4] Video Container - stream via PC Host / FTP',26),
    ('WEBM','[WEBM] Web Media Container - stream via PC Host / FTP',26),
    ('CONTROLS','D-Pad: Select Track | A: Play/Pause | X: Stop | FTP Port 5000 Active',22),
    ('RETURN','B or Minus to return to HBLauncher',24)
]
for name,label,size in items:
    face=ImageFont.truetype(font,size);box=draw.textbbox((0,0),label,font=face);w,h=box[2]-box[0],box[3]-box[1]
    draw.text((2-box[0],y-box[1]),label,font=face,fill=255)
    header.append(f'const ivec4 TEXT_{name} = ivec4(2, {y}, {w}, {h});');y+=h+8
(root/'assets/text.bin').write_bytes(atlas.tobytes());(root/'shaders/text.glsl').write_text('\n'.join(header)+'\n')

im=Image.new('RGBA',(256,256),(20,30,50,255));d=ImageDraw.Draw(im)
d.rounded_rectangle((26,42,230,214),radius=22,fill=(35,65,95),outline=(80,220,240),width=5)
d.polygon([(100,80), (100,176), (180,128)], fill=(111,246,221))
im.save(root/'assets/icon.png')
