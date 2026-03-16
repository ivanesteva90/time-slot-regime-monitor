# Time-Slot Regime Monitor

Proyecto para analizar y monitorear los mejores horarios intradia de un universo de estrategias en opciones, comparando multiples CSV y sugiriendo una estrategia combinada interpretable.

## Meta

Encontrar:

* el mejor horario actual
* el siguiente mejor horario probable
* señales de agotamiento del lider actual

## Datasets

`data/*.csv`

## Dashboard

`dashboard.html`

Abre el archivo en el navegador y sube uno o varios CSV, o la carpeta `data` completa, para recalcular:

* ranking intradia por dataset
* screener adicional Top 5 estrategias con filtros de fecha y hora
* comparacion global entre datasets
* score de agotamiento por horario
* estrategia combinada sugerida
* validacion walk-forward

## Nueva guia para Codex

Consulta `AGENTS.md` para instrucciones del motor de investigacion de SPX IC y reglas de sizing/regimen. Los CSV pueden venir de `data/` o de subcarpetas como `BTM/rut`, `BTM/spx`, `BTM/xsp`; el pipeline debe ingerir lo que el usuario suba.

## Referencia inicial

En el dataset original `agresivo_iron_condor_spx`, la primera lectura apuntaba a:

* Lider inicial: `11:15`
* Siguiente candidato inicial: `11:25`
