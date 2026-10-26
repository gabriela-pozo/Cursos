# Muestra ligera publicable

Copias reducidas de 6 documentos del corpus, para que el explorador del dashboard (`app.py`) muestre
la imagen junto al texto del OCR. Los originales están en `datos/raw/`, que no se versiona.

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

Atribución sugerida al reutilizar estas imágenes: «Fuente: [institución o autora], vía el proyecto
Tarea 2 de Gabriela Pozo (github.com/gabriela-pozo/Cursos)».

No se incluyó la foto de *Regulación económica*: es una página de un libro, y aunque la foto es
propia, el texto tiene derechos de su editorial.
