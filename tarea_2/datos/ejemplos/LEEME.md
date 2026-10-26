# Muestra ligera publicable

Copias reducidas de 6 documentos y 4 audios del corpus, para que los exploradores del dashboard (`app.py`) muestren
la imagen junto al texto del OCR y reproduzcan el audio. Los originales están en `datos/raw/`, que no se versiona.

Las 6 imágenes son parte de la muestra de evaluación de `02_evaluacion.ipynb` (tienen CER medido).
Se redujeron a 1000 px de ancho (JPEG, calidad 80) y se les quitaron los metadatos EXIF. Cada archivo
se llama como el `id` del documento en `datos/documentos.csv`.

| Archivo | Documento | Fuente y licencia |
|---|---|---|
| `imp_Memoria_BCRP_1922_p002.jpg` | Memoria del Banco Central de Reserva del Perú de 1922, p. 2 | Banco Central de Reserva del Perú, <https://www.bcrp.gob.pe/docs/Publicaciones/Memoria/Memoria-BCRP-1922.pdf>. Reproducción permitida citando la fuente (condiciones de uso del portal del BCRP) |
| `imp_Memoria_BCRP_1923_p003.jpg` | Memoria del Banco Central de Reserva del Perú de 1923, p. 3 | Banco Central de Reserva del Perú, <https://www.bcrp.gob.pe/docs/Publicaciones/Memoria/Memoria-BCRP-1923.pdf>. Reproducción permitida citando la fuente |
| `imp_Manuscrito_31_PE_1352_Carta_escrita_a_Don_Agust_n_Gamarra_p003.jpg` | *Carta escrita a Don Agustín Gamarra* (Guayaquil, 1832), p. 3 | Repositorio de la PUCP, Instituto Riva-Agüero (Manuscrito 31, PE 1352). CC0 1.0 |
| `fot_Foto_sintesis_reporte_marzo_2019.jpg` | Foto de la *Síntesis del Reporte de Inflación*, marzo de 2019 | Foto propia de la autora. Contenido: Banco Central de Reserva del Perú, reproducción permitida citando la fuente |
| `fot_Foto_boletas.jpg` | Foto de una boleta electrónica de Talleres Qosqo Maki (Cusco) | Foto propia de la autora. Sin datos de una persona: el cliente es "CLIENTE EVENTUAL" con DNI genérico 00000001; RUC, dirección y teléfono son de la empresa emisora (ver Decisión 2 en `01_extraccion.ipynb`) |
| `man_Manuscrito_cuaderno3.jpg` | Apuntes manuscritos propios sobre una evaluación de impacto | Manuscrito propio de la autora, sin datos personales |

## Audio

Muestra ligera para la reproducción en el dashboard: 3 clips de la muestra de evaluación (tienen
WER medido en `02_evaluacion.ipynb`) y un extracto de 40 s de la entrevista. Están en mp3 mono a
16 kHz y 32 kbps (unos 4 KB por segundo, 244 KB en total). Cada archivo se llama como el `id` del
audio en `datos/transcripciones.csv`. **El tramo con música de la entrevista no se publica**: la
canción "A La Molina" (Hermanos Santa Cruz) tiene derechos de terceros sin licencia declarada.

| Archivo | Audio | Fuente y licencia |
|---|---|---|
| `aud_pef_09697_01125907528.mp3` | Clip de OpenSLR 73, hablante `pef_09697` (mujer), 8,0 s | OpenSLR 73, corpus de español peruano de Google, <https://www.openslr.org/73/>. CC BY-SA 4.0 |
| `aud_pef_03397_00786843445.mp3` | Clip de OpenSLR 73, hablante `pef_03397` (mujer), 6,3 s | OpenSLR 73, <https://www.openslr.org/73/>. CC BY-SA 4.0 |
| `aud_pem_08421_00033745102.mp3` | Clip de OpenSLR 73, hablante `pem_08421` (hombre), 7,5 s | OpenSLR 73, <https://www.openslr.org/73/>. CC BY-SA 4.0 |
| `aud_espika_20201121_conversacion.mp3` | **Extracto de 40 s** (0:30 a 1:10) del tramo de conversación, que va de 07:00 a 13:00 del programa. Se oyen el entrevistado y, desde el segundo 21 del extracto, el conductor. La transcripción del extracto no contiene el nombre del entrevistado | Espika FM 90.7, *Al mundo le falta un tornillo*, 21/11/2020, bloque 4, <https://archive.org/details/espika-fm-al-mundo-le-falta-un-tornillo-20201121>. CC BY-SA 4.0 |

Los mp3 se derivan de los originales (corte, mezcla a mono, 16 kHz y compresión) y se comparten
con la misma licencia CC BY-SA 4.0.

## Atribución

Atribución sugerida al reutilizar estos archivos: «Fuente: [institución o autora], vía el proyecto
Tarea 2 de Gabriela Pozo (github.com/gabriela-pozo/Cursos)».

No se incluyó la foto de *Regulación económica*: es una página de un libro, y aunque la foto es
propia, el texto tiene derechos de su editorial.
