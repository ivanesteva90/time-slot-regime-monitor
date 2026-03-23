# Proyecto: Time-Slot Regime Monitor

## Objetivo

Desarrollar un motor analitico que use multiples archivos historicos dentro de `data/` para:

1. Pronosticar el siguiente mejor horario para operar.
2. Detectar si el mejor horario actual se esta agotando.
3. Rankear horarios con una metodologia matematica robusta.
4. Comparar datasets de distintas estrategias, perfiles y subyacentes sin sesgo de escala.
5. Sugerir una estrategia combinada interpretable.
6. Evitar sesgo por sobreajuste a periodos demasiado cortos.

## Datos disponibles

Carpeta principal:

* `data/*.csv`

Columnas de interes inicial:

* `Date`
* `Hora`
* `P/L`

## Hallazgos previos

Con el analisis inicial ya hecho:

* El mejor horario actual parece ser `11:15`.
* El siguiente mejor horario pronosticado parece ser `11:25`.
* Tambien hay horarios calientes de corto plazo como `11:50` y `12:05`, pero mas fragiles estructuralmente.
* El `11:15` muestra senales de posible agotamiento:

  * cayo fuerte en rendimiento de corto plazo frente a su media reciente
  * perdio rango relativo en ventana corta
  * el ultimo bloque de dias es peor que el bloque anterior

## Reglas conceptuales deseadas

El sistema debe usar un enfoque hibrido:

* largo plazo para robustez estructural
* mediano plazo para regimen actual
* corto plazo para momentum / desaceleracion

Idea de pesos iniciales:

* 55% largo plazo
* 30% mediano plazo
* 15% corto plazo

## Que quiero que construyas

1. Un pipeline que limpie y normalice la data por fecha y horario.
2. Un dashboard unico en `HTML5 + CSS3 + JavaScript` que permita subir uno o varios CSV, o una carpeta completa, y ejecutar localmente los mismos calculos sin backend.
3. Metricas rolling por horario:

   * avg P/L 10d, 21d, 63d, 126d, 252d
   * win rate
   * std dev
   * profit factor
   * max drawdown
   * consistencia trimestral
4. Un score pronostico del proximo mejor horario.
5. Un indice de agotamiento del horario lider actual.
6. Un ranking final tipo:

   * KEEP
   * WATCH
   * ROTATE
7. Una comparacion global entre datasets.
8. Una sugerencia de estrategia combinada tipo core / satellite / diversifier.
9. Un modulo adicional tipo screener para calcular Top 5 estrategias usando filtros de fecha, hora y criterios como rentabilidad, win rate y menor drawdown.
10. Validacion walk-forward para evitar look-ahead bias.

## Definicion deseada de agotamiento

Un horario debe marcarse como agotandose si empieza a cumplir varias de estas senales:

* rank 21d cae mucho frente a rank 63d
* avg 10d cae por debajo de ~70% de avg 63d
* avg 10d < avg del bloque previo de 10d
* win rate corto cae materialmente frente al mediano

## Entregables esperados

Quiero que generes:

1. Un `dashboard.html` autosuficiente como pieza principal
2. Un archivo con ranking actual de horarios por dataset
3. Un archivo con score de agotamiento por horario
4. Una comparacion global de datasets
5. Una salida adicional tipo Top 5 estrategias con navegacion al detalle del dataset y slot elegidos
6. Una explicacion breve de la metodologia
7. Recomendaciones para produccion / actualizacion periodica

## Restricciones

* No usar magia negra ni sobreajuste innecesario.
* Priorizar interpretabilidad.
* Primero construir version simple y robusta.
* Luego proponer mejoras con features adicionales solo si agregan valor real.
