#!/usr/bin/env bash
# Corre toda la tubería. Requiere los datos en data/raw/ (ver data/raw/README.md)
# Para regenerar solo el dashboard desde data/processed/: bash run_all.sh web
set -euo pipefail
cd "$(dirname "$0")"
RAW=data/raw; OUT=data/processed
if [ "${1:-}" != "web" ]; then
  python scripts/01_parse_inei.py $RAW/inei_tabulados $OUT
  python scripts/01b_parse_extra.py $RAW/inei_tabulados $OUT
  python scripts/01c_parse_lengua_flujos.py $RAW/inei_tabulados $OUT
  python scripts/02_padron_distrito.py $RAW/Padron.dbf $OUT/padron_distrito.csv
  python scripts/02b_ugel.py $RAW/Padron.dbf $OUT/ugel_distrito.csv
  python scripts/03_match_ubigeo.py $OUT/padron_distrito.csv $OUT/edades_distrito.csv $OUT/crosswalk.csv
  python scripts/04_indicators.py config.json $OUT
fi
python scripts/04b_prioridad.py config.json $OUT
python scripts/05_build_web.py $OUT/indicadores_distrito.csv $OUT/prioridad_distrito.csv $RAW/peru_distrital_simple.geojson web/data
python scripts/05b_findings.py config.json $OUT web/data docs
if [ "${1:-}" != "web" ]; then
  python scripts/06_reel_frames.py $OUT web/data/geometria.js reel/frames "${DASHBOARD_URL:-Enlace en la descripción}"
  python scripts/07_make_reel.py reel
fi
python -m unittest discover tests
