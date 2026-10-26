# Auditoria de la extraccion con LLM (Parte 2)

20 extracciones elegidas al azar de `datos/extraccion_llm.csv` con semilla `20261025` (ver `02_evaluacion.ipynb`, seccion 10). Para cada una: el texto fuente (primeros 800 caracteres; el LLM recibio hasta 3000) y el JSON extraido.

Escribe el veredicto despues de `**Veredicto:**`. No borres los encabezados `## n. id: ...`.

---

## 1. id: aud_pef_01208_01193903051

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Si vive en una zona donde el nivel de agua puede subir, considere levantar los muebles con ladrillos.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "agua",
  "resumen": "Considerar levantar los muebles con ladrillos si vive en una zona donde el nivel de agua puede subir.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — todos los campos aparecen en el texto y los ausentes están en null.

---

## 2. id: aud_pef_01523_00025987806

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
¿Cuáles son los reglamentos de usar las bicicletas de la ciudad?
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "regulamentación bicicleta",
  "resumen": "La ciudad ha establecido regulaciones para la utilización de bicicletas.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — invención: el texto es una pregunta y el modelo la convierte en una afirmación ("la ciudad ha establecido regulaciones"), que no está en el audio.

---

## 3. id: aud_pef_02484_00239124837

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Te voy a compartir la canción por WhatsApp.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: dejó tema y resumen en null, y también organizaciones, pese a que "WhatsApp" aparece en el texto.


---

## 4. id: aud_pef_02484_00800951599

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Quiero comprar un perro, pero la verdad es que no tengo idea de las razas.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto - omitió tema y resumen, el primero puede ser compra de un perro y el segundo una persona quiere comprarlo, pero desconoce las razas.

---

## 5. id: aud_pef_03397_00105310998

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Para hacer esa receta necesitas una cebolla y dos dientes de ajo.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: dejó tema y resumen en null, y también cifras, pese a que el texto trae cantidades ("una cebolla", "dos dientes de ajo").

---

## 6. id: aud_pef_04310_01779939240

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
¿Cuáles fueron las consecuencias de este movimiento?
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omitió resumen, que sí se podía escribir a partir del texto.

---

## 7. id: aud_pef_08784_01624964367

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Por las tardes escucha música en la plaza.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omitió resumen, tema y lugar; "la plaza" sí aparece en el texto.

---

## 8. id: aud_pef_09334_02028756242

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Ayer estuve en un museo de arte moderno y vi una exposición buenísima.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": "Vi una exposición buena en un museo de arte moderno.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — el resumen es fiel al texto y no inventa nada; omitió tema, que se podía poner.

---

## 9. id: aud_pef_09697_00704431274

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
¿Qué tipo de temas le gustaría escuchar?
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: dejó resumen y tema en null pudiendo resumir la pregunta.

---

## 10. id: aud_pem_00610_00202153686

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
La yoga además de relajarte y equilibrar tu organismo también te permitirá tonificar los brazos y las piernas
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "yoga",
  "resumen": "Tonificar los brazos y las piernas.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — tema y resumen salen del texto, sin inventar; el resumen es parcial (omite relajación y equilibrio).

---

## 11. id: aud_pem_00610_00826490796

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
¿Conoce la información nutricional de la pisa vegetariana?
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "nutrición",
  "resumen": "La pisa vegetariana es conocida por su alta cantidad de proteínas y minerales.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — invención: el texto es una pregunta, y el modelo la convirtió en una afirmación sobre proteínas y minerales que no está en el audio.

---

## 12. id: aud_pem_01208_00341280385

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Nuria, ¿podrías proponerme una obra de teatro para hoy en la noche?
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: todos los campos en null pudiendo resumir la petición; el tema podría ser "obra de teatro" y el texto trae además una referencia temporal ("hoy en la noche")

---

## 13. id: aud_pem_01208_00999759644

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Mañana vaya abrigada, un gorro de lana y guantes es lo más recomendable.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: dejó resumen y tema en null pudiendo resumir la petición.

---

## 14. id: aud_pem_03349_00797280590

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Me ayudes a buscar una tienda donde pueda comprarle un regalo a mi abuela.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: dejó resumen y tema en null pudiendo resumir la petición.

---

## 15. id: aud_pem_07049_00541469161

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Estoy aburría de desayunarse real, quiero que me recomiendes un desayuno rápido y saludable.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "desayuno",
  "resumen": "Desayuno rápido y saludable.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — tema y resumen salen del texto, sin inventar; el resumen es parcial, repite el final de la frase.

---

## 16. id: aud_pem_07505_00312036665

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Tienes que entrar al metro por la línea 9. Según Google, esta línea tiene 3 estaciones de transbordo.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "metro",
  "resumen": "Google afirma que la línea 9 tiene 3 estaciones de transbordo.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — no inventa y el resumen es fiel; pero dejó `cifras` y `organizaciones` en null pese a que ambos datos aparecen en su propio resumen: los mencionó sin estructurarlos.

---

## 17. id: aud_pem_07508_01835777824

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Me gustan demasiado las películas de ciencia ficción.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "ciencia ficción",
  "resumen": "La película me gusta mucho.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — tema exacto y no añade hechos nuevos; pero el resumen singulariza: el texto habla de un gusto por el género y el resumen suena a una película concreta.

---

## 18. id: aud_pem_09334_01372052575

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Voy a la Ciudad de México por cuatro días.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": null,
  "resumen": null,
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** incorrecto — omisión: todos los campos en null pese a que el texto trae un lugar explícito ("Ciudad de México") y una cantidad ("cuatro días").

---

## 19. id: aud_pem_09697_01192411833

Modalidad: audio · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
Quiero tener una mascota a quien le pueda decir mis sentimientos.
```

**JSON extraido:**

```json
{
  "modalidad": "audio",
  "tema": "sentimientos",
  "resumen": "La persona desea tener una mascota para comunicar sus emociones.",
  "fecha": null,
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — resumen fiel y completo, no un fragmento copiado; los campos sin dato están correctamente en null.

---

## 20. id: imp_Memoria_BCRP_1923_p003

Modalidad: documento · modelo: Qwen/Qwen2.5-0.5B-Instruct (transformers, CPU, float32, greedy)

**Texto fuente (primeros 800 caracteres):**

```text
2 variando desde un mínimumde Lp.211,629 en Marzo hasta un máximum de Lp.642,90l durante el mes de Octubre, como puede verse en el cuadro N°. 3 y en el diagrama B. No creemos necesario comparar el monto de estas operaciones con las del año anterior, pues como ese fué el primero de la existencia del Banco, sus facilidades recién comenzaban a ser utilizadas por los Ban- cos Asociados Las operaciones de descuento y redescuento han producido una uti- lidad de Lp.42,280.3.37. Nos es sumamente satisfactorio dejar constancia de que durante el año que reseñamos se ha hecho un uso juicioso del crédito. Analizando los balances de todos los bancos de Lima correspondientes a los 10 pri- meros meses de 1923, se nota que las inversiones y los depósitos a la vista y a plazo han experimentado un desarroll
```

**JSON extraido:**

```json
{
  "modalidad": "documento",
  "tema": "Banco Peruano",
  "resumen": "La mayor parte de los bancos peruinos mantienen un encaje de moneda nacional bajo control, aunque algunos han incrementado su encaje en monedas extranjeras debido a la facilitad de operar con un menor encaje.",
  "fecha": "1923",
  "lugar": null,
  "organizaciones": null,
  "cifras": null
}
```

**Veredicto:** correcto — el resumen habla de "encaje", que sí aparece en el texto completo aunque no en el extracto de 800 caracteres; no inventa. Dejó `cifras` en null habiendo tres montos en libras peruanas (Lp.211,629, Lp.642,90l, Lp.42,280.3.37); además introdujo una errata propia ("peruinos" por "peruanos") sobre un texto de entrada limpio.