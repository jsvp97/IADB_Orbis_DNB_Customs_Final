# Paper agro: entrega de la ronda v6 de estimaciones (28 de noviembre de 2026)

Esta ronda corre el núcleo del documento `especificaciones_estimaciones_v6_2026-11-25` (V6-01 a V6-18). El segundo nivel (V6-19 a V6-31) queda para cuando se haya revisado el núcleo. El texto del paper sigue en la versión v4.

## Qué hay en cada carpeta

| Carpeta | Contenido |
|---|---|
| `1_resultados/` | `WP_paperagro_v6_master_estimates.xlsx`: todas las estimaciones, en 106 hojas. `RESULTS_v6_2026-11-27.md`: el registro de la ronda, con lo que se pidió, lo que se corrió, cada resultado (también los nulos y los de signo contrario), lo que no se pudo estimar y por qué, y las propuestas aparte. |
| `2_figuras/` | Las seis figuras de la v6, en PDF y PNG. No hay figura 6: el nivel de partida HS4 no se pudo estimar porque hay 86 partidas tratadas y el umbral es 150. |
| `3_codigo/` | Los scripts de Python y los do-files de Stata de las rondas v4, v5 y v6, en el orden en que se corren. Su `README.md` explica qué hace cada uno. |

## Por dónde empezar

1. **El registro.** La sección 6 tiene la tabla del conjunto primario (T1 a T6 y el diagnóstico DG). Así se atendieron los tres comentarios a la v5:
   - **las cohortes alineadas:** la sección 3 dice qué hacía mal la regla de la v5, y la sección 7 trae los resultados con los stacks alineados;
   - **la cohorte 2017 y el cambio a HS 2017:** sección 5 y punto 2 de la sección 8;
   - **el promedio de OLS, que dividía por cinco:** está corregido en todas las hojas del Excel que lo usan.
2. **En el Excel, las hojas `Read me` y `Main results`.** `Main results` abre con la tabla del conjunto primario. Las hojas nuevas de la v6 van de la 10.1 a la 12.7. La hoja `All estimates, one per row` tiene una fila por coeficiente, y su columna `Role` dice si el resultado es primario, diagnóstico, secundario, de robustez, descriptivo o exploratorio.
3. **Las figuras.** En el Excel, la hoja `8.0 Figure index` describe cada figura, y la hoja `8.2 Figure data, after entry` tiene los números detrás de las figuras de la v6.
4. **El código**, si se quieren revisar las definiciones. El registro dice qué script y qué bloque produce cada resultado.

## Qué no se incluye

No van datos, archivos intermedios ni salidas de los programas. La base de aduanas emparejada con Orbis y D&B es confidencial. El código corre en el equipo donde está esa base. Las rutas están en `3_codigo/config/paths.py` y al principio de cada do-file.
