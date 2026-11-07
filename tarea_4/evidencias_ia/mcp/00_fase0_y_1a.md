 ▐▛███▛█   Claude Code v2.1.319
▝▜██████▀  Sonnet 5.5 · Claude Pro
 ▝▝   ▝▝   ~\Documents\GitHub\Cursos\tarea_4


❯ Trabajo la Tarea 4 del curso Python Intermedio (issue #201 de                 
  d2cml-ai/Data-Science-Python): un agente que combina un servidor MCP del      
  BCRP (FastMCP) con 3 Skills de Claude Code para la ENAHO 2024.                
  Uso Windows. El proyecto vive en                                              
  C:\Users\Asus\Documents\GitHub\Cursos\tarea_4 y el repo del curso está        
  clonado en C:\Users\Asus\Documents\GitHub\Data-Science-Python.                
                                                                                
  Reglas para toda la sesión:                                                   
  - Soy estudiante: antes de codificar dime el plan, y al terminar explícame    
    qué hiciste y por qué, en lenguaje simple.                                  
  - Trabaja solo en la fase que te pida y detente al terminar.                  
  - No modifiques las 8 pruebas originales de la sesión 04.                     
  - Ninguna cifra se escribe a mano; todo sale de procesar datos.               
  - Si una validación falla, detén el proceso con error explícito; no ajustes   
    resultados. Si una herramienta falla, repórtalo; no inventes.               
  - ENAHO siempre ponderada; no presentes asociaciones como causales.           
  - Sin claves ni microdatos en el repo. Commit descriptivo al cerrar cada      
  fase.                                                                         
  - Usa rutas con pathlib para que el código funcione en Windows y otros        
  sistemas.                                                                     
                                                                                
  FASE 0:                                                                       
  1. Crea la estructura en tarea_4/: mcp/, .claude/skills/{limpiando-enaho,     
     graficando-enaho,mapeando-enaho}/, datos/, salidas/, figuras/, mapas/,     
     evaluacion/, informes/,                                                    
  evidencias_ia/{mcp,skills,integracion,evaluacion}/,                           
     más pyproject.toml con uv (fastmcp, pandas, pyarrow, geopandas,            
     matplotlib, pytest) y .gitignore (datos/, entornos virtuales,              
  __pycache__).                                                                 
  2. Lee sessions/04-mcp-claude-code/ y sessions/16-skills-enaho/ del repo del  
     curso. No escribas código del proyecto todavía.                            
  3. Crea datos/descargar.py para bajar ENAHO 2024 módulos 34 y 02 (STATA) y    
     el GeoJSON departamental con los enlaces del issue #201, y ejecútalo.      
  4. Resúmeme: qué trae cada sesión, qué herramientas y pruebas tiene el        
     proyecto de la sesión 04, y qué reglas de ENAHO define la sesión 16.       
  5. Haz un commit y detente. Espera mi OK.                                     

● Plan breve de la Fase 0:
  1. Crear la estructura de carpetas, pyproject.toml y .gitignore.
  2. Leer las sesiones 04 y 16 del repo del curso, sin escribir código del
     proyecto.
  3. Leer el issue #201 para obtener los enlaces, escribir datos/descargar.py y
     ejecutarlo.
  4. Resumirte lo leído y hacer el commit.

  Empiezo con el estado actual y el issue.

  Ran 1 shell command (ctrl+o to expand)

● gh no está instalado. Pruebo la API pública de GitHub con curl y leo las
  sesiones en paralelo.

  Read 1 file, ran 5 shell commands (ctrl+o to expand)

● Tengo el issue completo, con los 3 enlaces de descarga. Ahora leo las
  sesiones.

  Ran 2 shell commands (ctrl+o to expand)

● Ya tengo todo lo necesario. Creo la estructura, el pyproject.toml y el
  .gitignore.

  Ran 1 shell command (ctrl+o to expand)

● La descarga funcionó y los tamaños coinciden con la sesión 16 (16 MB y 6 MB).
  Reviso qué archivos llegaron, valido el pyproject.toml con uv y confirmo que
  Git ignora los datos.

  Ran 1 shell command (ctrl+o to expand)

● Todo está en orden. Hago el commit solo con tarea_4/. No añado la línea de
  coautoría, porque tu regla guardada lo prohíbe.

  Ran 1 shell command (ctrl+o to expand)

● La Fase 0 está terminada y el commit es 2a809e2. No hice push, y paro aquí
  hasta que me des tu OK.

  Qué hice y por qué

  - Estructura: creé todas las carpetas que pide el issue. Las vacías llevan un
    archivo .gitkeep, porque Git no guarda carpetas vacías.
  - pyproject.toml: declara fastmcp, pandas, pyarrow, geopandas, matplotlib y
    pytest. Corrí uv lock y resolvió bien las 88 dependencias; el uv.lock quedó
    en el commit para que otra persona obtenga las mismas versiones.
  - .gitignore: ignora datos/*, los entornos virtuales y __pycache__. Dejé una
    excepción para datos/descargar.py. Sin ella, datos/ completo se habría
    ignorado y el script de descarga no se habría subido.
  - datos/descargar.py: baja los módulos 34 y 02 y el GeoJSON con los enlaces
    del issue, y descomprime los zip. Si una descarga falla, termina con error y
    no inventa nada. Lo ejecuté y bajó los tres archivos: 16 MB, 6 MB y 0.1 MB,
    igual que en la sesión 16.
  - Issue #201: no tenía gh, así que leí el issue completo con la API pública de
    GitHub.

  Sesión 04 (MCP)

  - Qué trae: qué es MCP, cómo se usa en Claude Code (claude mcp add) y cómo se
    construye un servidor con FastMCP. Mide cuántas cifras acierta Claude sin
    MCP y con él.
  - Servidor server.py: solo buscar_series funciona. Faltan cinco TODO: serie,
    resumen, una herramienta propia, un recurso y un prompt. El catálogo del
    BCRP (unas 17 mil series) se baja una vez a datos/.
  - Pruebas: test_server.py tiene 8, con datos reales del BCRP, y no se debe
    tocar. Cubren estos puntos:
    - buscar_series encuentra el IPC.
    - Hay al menos 4 herramientas.
    - serie mensual y diaria.
    - resumen.
    - Un código inexistente da un error que lo nombra.
    - Hay un recurso.
    - Hay un prompt.
  - Estado de partida: el README dice que empieza en 1 pasa y 7 fallan, y la
    meta es 8 de 8.
  - Evaluación: evaluar.py le hace 8 preguntas de preguntas.csv a Claude con
    claude -p en modos memoria, web y mcp. La tarea exige 10 preguntas (aquí 4
    BCRP, 4 ENAHO y 2 mixtas) y 2 pruebas propias.
  - API del BCRP: los meses llegan como Ene.2025, los días como 01.Oct.26 y
    setiembre como Set. Si recibe muchos pedidos seguidos, responde HTML en vez
    de JSON.

  Sesión 16 (Skills ENAHO)

  - Qué trae: qué es una skill (una carpeta con SKILL.md y scripts) y cómo se
    activa. Lo no negociable va en un script y lo que requiere criterio va en el
    texto.
  - Reglas de ENAHO:
    - Lectura: pd.read_stata(..., convert_categoricals=False) con las llaves
      como texto, para no perder ceros. Los nombres van en minúscula (la columna
      del año llega como aÑo).
    - Llaves: conglome, vivienda, hogar, y codperso en personas.
    - Residentes habituales: ((p204==1)&(p205==2)) | ((p204==2)&(p206==1)).
    - Unión: merge(..., validate="m:1").
    - Variables: departamento = ubigeo[:2], urbano = estrato <= 5 y pobre = 
      pobreza <= 2.
    - Ponderación: facpob07 en personas y factor07 en hogares.
    - Validación: pobreza 27.6 %, 108,664 residentes de 117,721 filas, urbano
      24.8 % y rural 39.3 %.
    - Gráficos: siempre ponderados, barras desde cero y ordenadas, título que
      diga qué y cuándo, y nota "Fuente: INEI, ENAHO 2024".
    - Mapa: une por ubigeo[:2] con FIRST_IDDP, nunca por nombre. Pide 25
      departamentos con Lima (15) y Callao (07) separados, y un solo color de
      claro a oscuro.
    - Coordinación: graficar y mapear deben llamar primero a limpiando-enaho si
      falta salidas/personas_2024.parquet.
  - Referencias: referencias/pobreza_departamento_2024.csv (25 filas) y
    mapa_pobreza_2024.png.

  Cosas que vi y que pesarán en la Fase 1

  - Los zip se extraen en carpetas anidadas, por ejemplo
    datos/966-Modulo34/966-Modulo34/. El script de limpieza tendrá que buscar
    ahí.
  - El módulo 34 trae dos sumarias: sumaria-2024.dta (hogares) y
    sumaria-2024-12g.dta. La sesión 16 usa 33,691 hogares, así que hay que
    comprobar cuál corresponde antes de usarla.
  - El README de la sesión 16 no usa el año 2024 como argumento fijo en todos
    lados, pero nosotros sí validaremos contra 2024.

  ¿Pasamos a la Fase 1? Si me das el OK, te presento el plan antes de escribir
  código.

✻ Brewed for 5m 45s · done 4:06 PM

※ recap: Estás armando la Tarea 4: un agente que combina el MCP del BCRP con tres Skills de ENAHO 2024. La Fase 0 (estructura, descarga de datos y commit 2a809e2) está lista, y lo siguiente es que me des tu OK para presentarte el plan de la Fase 1. (disable recaps in /config)