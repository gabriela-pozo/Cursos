# Corre los tres pedidos con y sin skills. Antes de cada uno borra la base limpia para ver si se encadenan las skills.
Set-Location (Split-Path $PSScriptRoot)
$pedidos = @(
    "¿Cuál fue la pobreza en Cusco en 2024? Usa la ENAHO.",
    "Grafica la pobreza urbana y rural con la ENAHO 2024",
    "Haz un mapa de la pobreza por departamento con la ENAHO 2024"
)
for ($i = 0; $i -lt 3; $i++) {
    foreach ($modo in "con", "sin") {
        Remove-Item salidas/personas_2024.parquet -ErrorAction SilentlyContinue
        $extra = if ($modo -eq "sin") { @("--disallowedTools", "Skill") } else { @() }
        Write-Host "Pedido $($i+1), $modo skills..."
        claude -p $pedidos[$i] @extra --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep" `
            --output-format stream-json --verbose | Out-File -Encoding utf8 "eval_logs/p$($i+1)_$modo.jsonl"
    }
}
# Regenera las salidas oficiales con los scripts de las skills
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024 | Out-Null
foreach ($x in "area", "sexo", "edad") { uv run .claude/skills/graficando-enaho/scripts/graficar.py $x | Out-Null }
uv run .claude/skills/mapeando-enaho/scripts/mapear.py | Out-Null
# Resumen: skills activadas y respuesta final de cada corrida
Get-ChildItem eval_logs/*.jsonl | ForEach-Object {
    $skills = @(Select-String -Path $_ -Pattern '"skill":"([a-z-]+)"' -AllMatches).Matches | Where-Object { $_ } | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    $res = Get-Content $_ | Where-Object { $_ -match '"type":"result"' } | ForEach-Object { ($_ | ConvertFrom-Json).result }
    "== $($_.Name): skills = $($skills -join ', ')"
    $res
}
