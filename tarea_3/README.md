# Entrega · Sesión 15 · Del texto a tu voz: reels con modelos abiertos

**Nombre:** Gabriela  
**Texto que usaste:** Síntesis del Reporte de Inflación, BCRP, setiembre de 2026 (5 páginas), de mi carrera  
**Link de tu repo:** https://github.com/gabriela-pozo/Cursos/tree/main/tarea_3  
**Fecha:** 24 de octubre de 2026

## 1. Archivos de la entrega: del texto a tu voz

| Archivo | Qué es |
|---|---|
| `reel.mp4` | Reel vertical de 53,7 s narrado con mi voz clonada, con subtítulos y el aviso «Voz generada con IA» |
| `posts.md` | Tres posts (LinkedIn, X y Facebook) revisados |
| `guion_qwen.json` | Guion generado por Qwen, sin corregir |
| `guion_deepseek.json` | Guion generado por DeepSeek, sin corregir |
| `guion_deepseek_corregido.json` | Guion de DeepSeek con mis correcciones (es el que se narró) |
| `portada.png`, `reel.srt` | Portada y subtítulos del reel |

Nivel que busco: **Excelente** (reel y posts revisados, correcciones explicadas y comparación Qwen vs DeepSeek).

El reel no se publica para no dejar mi voz pública; lo presento en clase.

## 2. ¿Cómo lo hice?

1. Generé el prompt con `guion.py` a partir del PDF y lo pegué en chat.qwen.ai y en chat.deepseek.com, con el mismo prompt y el mismo texto.
2. Revisé los dos guiones escena por escena contra el informe.
3. Elegí el de DeepSeek, lo corregí a mano y lo narré.
4. Voz: Qwen3-TTS 0,6B (clonada con una grabación mía de 22 s). Subtítulos y control de calidad: Whisper large-v3-turbo. Video: Pillow y ffmpeg.
5. Todo corrió en una laptop con Windows, sin GPU.

## 3. Resultado técnico

- Narración de **53,7 s** (dentro de los 30 a 60 s pedidos) y **139 palabras** subtituladas.
- Control de Whisper, palabras mal entendidas por escena: 0,04 · 0,00 · 0,06 · 0,05 · 0,09 · 0,04 · 0,00. Ninguna superó el 25 %, así que no se regeneró ninguna escena.
- Tiempo total del reel con modelos ya descargados: unos 7,7 minutos en CPU.

## 4. Mis correcciones al guion de DeepSeek

| Dónde | Qué decía el modelo | Qué dice el informe | Corrección |
|---|---|---|---|
| Escena 2 | El alza se explica por alimentos; la cifra mostrada era +4,37 % con etiqueta «Alimentos y energía» | 4,37 % es la inflación del grupo alimentos y energía juntos (cuadro de la p. 5); el texto atribuye el alza sobre todo a alimentos como pescado fresco, huevos y pollo | Etiqueta explícita («Inflación de alimentos y energía, ago. 2026»), frase con «sobre todo» y sin repetir la fecha |
| Escena 6 | El riesgo sube por El Niño Costero extraordinario | El balance de riesgos se revisa al alza sobre todo por el mayor riesgo de choques de oferta internos; el escenario base **supone** un Niño Costero extraordinario (p. 5) | Frase que separa el motivo (choques de oferta internos) del supuesto (El Niño) |
| Escena 7 | «Mira el tablero completo en mi perfil» (el prompt de `guion.py` pide ese tipo de cierre) | No existe ningún tablero | Cierre con el reporte completo en la web del BCRP |
| Posts | Mencionaban el tablero en los tres; en LinkedIn y Facebook la frase de El Niño tenía el mismo problema que la escena 6 | Igual que arriba | Se quitó el tablero y se corrigió la frase de El Niño; se mantuvo el aviso de IA |

## 5. Comparación Qwen vs DeepSeek (mismo prompt, mismo informe)

Clasifiqué los problemas en cinco tipos:

- **A. Persona o dato inventado** (el modelo habla como autor del informe).
- **B. Proyección o supuesto presentado como hecho.**
- **C. Etiqueta o cifra mal asociada.**
- **D. Imprecisión menor** (falta el período o el «interanual»).
- **E. Referencia inexistente** (el tablero).

| | Qwen | DeepSeek |
|---|---|---|
| Escenas totales | 6 | 7 |
| **Escenas con errores de fondo** (A, B o C) | **4 de 6** | **2 de 7** |
| A. Persona o dato inventado | 3 escenas (1, 3 y 4) y 2 posts | 0 |
| B. Proyección como hecho | 1 escena (3) y 3 posts | 1 escena (6) y 2 posts |
| C. Etiqueta o cifra mal asociada | 1 escena (2) | 1 escena (2) |
| D. Imprecisión menor | 2 escenas (4 y 5) | 0 |
| E. Referencia inexistente (tablero), **inducida por el prompt**: no se cuenta como error del modelo | 1 escena (6) y 3 posts | 1 escena (7) y 3 posts |
| Cifras correctas contra el informe | 5 de 5 | 6 de 6 |

**Ejemplos.** Qwen escribió «mi proyección de crecimiento» y «mis exportaciones se benefician», como si la autora fuera el BCRP y el país fueran suyos, y presentó El Niño como un hecho que ya bajó el crecimiento, cuando el informe lo trata como un supuesto de la proyección. DeepSeek se mantuvo más cerca del texto, pero mezcló una cifra de alimentos y energía con una frase solo de alimentos y atribuyó el alza del riesgo a El Niño en lugar de a los choques de oferta.

**Conclusión.** En esta prueba, **DeepSeek inventó menos que Qwen**: 2 de 7 escenas con errores de fondo frente a 4 de 6, y ninguna persona inventada. Ambos repitieron el «tablero en mi perfil», pero **no es un error de los modelos**: el prompt de `guion.py` les pide que la última escena invite a «ver el tablero» y trae como ejemplo «Mira el tablero: enlace en mi perfil» (líneas 28 y 38). Por eso no lo conté contra ninguno. Es **una sola corrida con un solo informe**, así que no sirve para afirmar que un modelo sea mejor en general.

## 6. Lo que la verificación automática no detectó

`guion.py` marcó **«ok» en las 6 escenas de Qwen y en las 7 de DeepSeek**, porque todas las cifras sí aparecen en el informe. Pero había frases falsas, inventadas o mal atribuidas, incluida una escena sin cifra que mencionaba un tablero inexistente. La verificación automática valida números, no afirmaciones. La revisión humana contra la fuente es la que detectó los errores, y fue necesaria antes de narrar.

## 7. Problemas técnicos en Windows

- **`UnicodeDecodeError` al leer `guion.json`:** `guion.py` lo escribió en la codificación ANSI de Windows y no en UTF-8. Lo resolví activando `PYTHONUTF8=1` en la terminal y guardando el guion corregido en UTF-8.
- **Rutas de Mac en los comandos del README:** usé `.venv\Scripts\python` en lugar de `.venv/bin/python` y no usé `--device mps`.
- **Avisos de `flash-attn`, `SoX` y symlinks de Hugging Face:** no bloquearon la ejecución.
- **Primera corrida lenta:** descargó unos 4 GB de modelos; la voz en CPU no muestra progreso mientras genera.

## 8. Limitaciones que observé en el reel y mejoras propuestas

Después de ver y escuchar el reel completo, noté tres problemas que ni la verificación de cifras ni el control de Whisper señalaron:

1. **La sigla «BCRP» no se entiende bien en la narración.** La voz clonada no la pronuncia con claridad. Las escenas que la contienen (la 1 y la 5) tuvieron un error de Whisper de 0,04 y 0,09, así que el control automático no las marcó como problema. **Mejora:** decir «el Banco Central» en las frases habladas (más fácil de pronunciar y de entender) y dejar «BCRP» solo en el texto escrito, como en los posts.
2. **En la escena de El Niño, el texto y la imagen no ayudan a entender el mensaje.** La pantalla muestra «El Niño» en letras gigantes, como si fuera una cifra, con la etiqueta «Supuesto de la proyección». La cifra «El Niño» la propuso DeepSeek; la etiqueta la escribí yo al corregir el guion, sin probar cómo se vería en pantalla. Juntas parecen un título sin explicación. La frase es larga y técnica («balance de riesgos», «choques de oferta», «escenario base»). Quien no conoce el informe no entiende qué significa ni por qué importa. **Mejora:** una frase más corta que diga el efecto («el BCRP supone un Fenómeno El Niño extraordinario; si se intensifica o dura más, la inflación podría ser mayor») y una etiqueta que lo explique.

3. **Los cambios de escena no coinciden del todo con la narración.** En las transiciones, la tarjeta de la escena siguiente aparece cuando la voz todavía no terminó la frase anterior, y los subtítulos mezclan el final de una escena con el inicio de la otra (por ejemplo, la franja mostró «mil veintisiete El balance» sobre la tarjeta de El Niño). Causa probable, por confirmar en `reel.py`: las tarjetas y los subtítulos se sincronizan con tiempos distintos en el límite entre escenas. **Mejora posible:** que cada tarjeta dure hasta la última palabra de su escena, o dejar una pausa corta entre escenas.

**Aprendizaje:** las verificaciones automáticas (cifras con ¡ y error de palabras de Whisper) no miden si el mensaje se entiende ni si se oye claro. Hay que ver y escuchar el reel final, además de leer el guion.

## 9. Reglas

- La voz clonada es **la mía**.
- El video y los tres posts declaran que la voz fue generada con IA.
- El guion completo fue leído contra el informe antes de narrarlo.
- Mi grabación de voz no se sube al repositorio.
