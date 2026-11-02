"""Genera la música de fondo del reel (original, sin derechos de terceros): acordes suaves Am - F - C - G.
Uso: python 06b_musica.py <salida.mp3>   (requiere numpy y ffmpeg)"""
import sys, wave, subprocess, tempfile, os
import numpy as np
sr, T = 44100, 82
t = np.arange(int(sr * T)) / sr
acordes = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
y = np.zeros_like(t)
for i in range(int(T // 8) + 1):
    a, b = i * 8, min((i + 1) * 8, T)
    if a >= T: break
    m = (t >= a) & (t < b); tt = t[m] - a
    env = np.minimum(1, tt / 1.5) * np.minimum(1, (b - a - tt) / 2.0)
    for f in acordes[i % 4]:
        y[m] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 1) + 0.15 * np.sin(2 * np.pi * (f * 1.003) * tt))
    y[m] += env * 0.5 * np.sin(2 * np.pi * (acordes[i % 4][0] / 2) * tt)
y *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
y = y / np.max(np.abs(y)) * 0.5 * np.minimum(1, t / 2) * np.minimum(1, (T - t) / 3)
s = (np.stack([y, np.roll(y, int(0.012 * sr))], 1) * 32767).astype('<i2')
tmp = os.path.join(tempfile.mkdtemp(), 'm.wav')
w = wave.open(tmp, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(s.tobytes()); w.close()
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-b:a', '128k', sys.argv[1]], check=True)
