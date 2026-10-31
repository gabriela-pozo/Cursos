"""Ensambla el reel: subtítulos sincronizados (SRT) y video 1080x1920.
- Si existen reel/audio/escena_N.wav (voz IA clonada de la autora), la duración de cada escena sale del audio.
- Si no, estima la duración por número de palabras y genera un preview sin voz.
- Si existe reel/musica.mp3 (pista con licencia), se mezcla a -22 dB bajo la voz.
Uso: python 07_make_reel.py [carpeta_reel]   (requiere ffmpeg con libass)"""
import json, os, re, subprocess, sys, textwrap
R = sys.argv[1] if len(sys.argv) > 1 else 'reel'
G = json.load(open(f'{R}/guion.json', encoding='utf-8')); FPS = G['formato']['fps']
def dur_audio(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode().strip())
scenes = []; t = 0.0
for s in G['escenas']:
    wav = f"{R}/audio/escena_{s['id']}.wav"; has = os.path.exists(wav)
    d = (dur_audio(wav) + 0.5) if has else len(s['narracion'].split()) / 2.6 + 0.6
    scenes.append({**s, 'wav': wav if has else None, 't0': t, 'dur': d}); t += d
total = t
def ts(x): h, m = int(x // 3600), int(x % 3600 // 60); s = x % 60; return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}'
srt = []; n = 1
for s in scenes:
    words = s['narracion'].split(); chunks, cur = [], ''
    for w in words:
        if len((cur + ' ' + w).strip()) > 34 and cur: chunks.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    if cur: chunks.append(cur)
    span = s['dur'] - 0.4; tot = sum(len(c) for c in chunks); a = s['t0'] + 0.1
    for c in chunks:
        b = a + span * len(c) / tot
        srt.append(f'{n}\n{ts(a)} --> {ts(b)}\n' + '\n'.join(textwrap.wrap(c, 24)) + '\n'); n += 1; a = b
open(f'{R}/subtitulos.srt', 'w', encoding='utf-8').write('\n'.join(srt))
# guion con tiempos
json.dump({**G, 'duracion_total_s': round(total, 1), 'escenas': [{k: v for k, v in s.items() if k != 'wav'} | {'t0': round(s['t0'], 2), 'dur': round(s['dur'], 2), 'con_audio': bool(s['wav'])} for s in scenes]},
          open(f'{R}/guion_con_tiempos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Duración total: {total:.1f} s ({"con voz" if all(s["wav"] for s in scenes) else "preview SIN voz"})')
# video
inputs, fl = [], []
for i, s in enumerate(scenes):
    inputs += ['-loop', '1', '-framerate', str(FPS), '-t', f"{s['dur']:.3f}", '-i', f"{R}/frames/escena_{s['id']}.png"]
    fl.append(f"[{i}:v]scale=1080:1920,format=yuv420p,fade=t=in:st=0:d=0.25,fade=t=out:st={s['dur']-0.25:.3f}:d=0.25[v{i}]")
k = len(scenes); fl.append(''.join(f'[v{i}]' for i in range(k)) + f'concat=n={k}:v=1:a=0[vc]')
# libass usa PlayRes 384x288 para SRT: tamaños en esas unidades (x6.67 en un video de 1920 px de alto)
sub = f"subtitles={R}/subtitulos.srt:force_style='Fontname=Inter,Fontsize=9,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=50,MarginL=12,MarginR=12'"
fl.append(f'[vc]{sub}[vout]')
# audio
if all(s['wav'] for s in scenes):
    ai = []
    for s in scenes:
        inputs += ['-i', s['wav']]; ai.append(len(inputs) // 2 - 1 + 0)
    base = k
    parts = ''.join(f'[{base+j}:a]apad=pad_dur={scenes[j]["dur"]:.3f},atrim=0:{scenes[j]["dur"]:.3f}[a{j}];' for j in range(k))
    fl.append(parts + ''.join(f'[a{j}]' for j in range(k)) + f'concat=n={k}:v=0:a=1[voz]')
    aout = '[voz]'
    if os.path.exists(f'{R}/musica.mp3'):
        inputs += ['-i', f'{R}/musica.mp3']; mi = k + k
        fl.append(f'[{mi}:a]volume=-22dB,atrim=0:{total:.2f},afade=t=out:st={total-2:.2f}:d=2[m];[voz][m]amix=inputs=2:duration=first:normalize=0[amix]'); aout = '[amix]'
    amap = ['-map', aout]
else:
    amap = []; inputs += ['-f', 'lavfi', '-t', f'{total:.2f}', '-i', 'anullsrc=r=44100:cl=stereo']; amap = ['-map', f'{k}:a']
cmd = ['ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(fl), '-map', '[vout]', *amap, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-r', str(FPS), '-shortest', f'{R}/reel.mp4']
subprocess.run(cmd, check=True); print('OK', f'{R}/reel.mp4', round(os.path.getsize(f'{R}/reel.mp4') / 1e6, 1), 'MB')
