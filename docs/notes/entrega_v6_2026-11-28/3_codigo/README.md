# Código de las rondas v4, v5 y v6 del paper agro

Esta carpeta trae solo código: los scripts de Python y los do-files de Stata. No incluye datos, archivos intermedios ni salidas. La base de aduanas emparejada con Orbis y D&B es confidencial y no sale del equipo de trabajo.

Los nombres de los archivos son los mismos del repositorio (`stylized_facts/python` y `stylized_facts/stata`). No se renumeraron porque los scripts se importan entre sí: un prefijo en el nombre rompería esas importaciones. El orden de ejecución está en la tabla de abajo.

## Cómo se corren

- **Python** 3.10, desde la carpeta `python/`, con las variables de entorno que indica cada fila. Paquetes usados: pandas 2.1.4, numpy 1.26.4, pyfixest 0.50.1, pyarrow 23.0.1, scipy 1.13.1, statsmodels 0.14.6, matplotlib 3.10.9, openpyxl 3.1.2, pyreadstat 1.3.5 y pycountry 26.2.16.
- **Stata** 18 MP: `StataMP-64.exe /e do <do-file> <argumentos>`. Comandos de SSC: reghdfe, ppmlhdfe, csdid, eventstudyinteract, did_imputation, did_multiplegt_dyn, jwdid, xtevent, honestdid y distinct.
  - Cada corrida usa su propia copia del do-file, en su propia carpeta. Stata lee el do-file línea por línea mientras corre, así que editarlo a mitad de una corrida la interrumpe.
- **Rutas:** las de Python están en `config/paths.py`, y `wp_common.py` lo busca una carpeta arriba de `python/`. Los do-files fijan la ruta en `global ROOT`, al principio de cada uno.

## Orden de ejecución

Los pasos 1 a 7 son la base común que usan las tres rondas.

| # | Archivo | Qué hace |
|---|---|---|
| 1 | python/_common.py | Funciones de apoyo del pipeline de hechos estilizados: rutas, estilo de gráficos y utilidades. Solo se importa. |
| 2 | python/wp_common.py | Rutas y lectura de la base firma × origen × destino × producto × año. Convierte los códigos a HS 2017 con las tablas de UNSD (`to_hs2017`) y corrige los códigos de Uruguay 2016 a 2018 que perdieron el cero inicial. Solo se importa. |
| 3 | python/wp_agro_croptype.py | Tipo de producción de cada producto agro (cultivos de campo, hortícolas y de plantación, ganadería y pesca, otros procesados), por partida HS4 y según los grupos de cultivos de la FAO. Solo se importa. |
| 4 | python/wp_agro_capital.py | Intensidad de capital de la industria estadounidense que produce cada producto: Censo Agropecuario 2017 para la etapa de finca y NBER-CES para la de procesamiento. Solo se importa. |
| 5 | python/wp_agro_classification.py | Arma la tabla de clasificaciones de los productos agro. Se corre una vez: `WP_YEARS=2012-2018 WP_HS17=1 python wp_agro_classification.py` |
| 6 | python/wp_agro_paper.py | Funciones de apoyo de las rondas anteriores, por ejemplo `real_dest`, que deja solo destinos que son países reales. Solo se importa. |
| 7 | python/wp_agro_note_v3.py | Código de la Note v3. La v4 lo reutiliza para las tablas descriptivas de 2018. Solo se importa. |
| **Ronda v4** | | |
| 8 | python/wp_agro_v4_data.py | Cubos de celdas odpy y opy, filas de firma por sector y clases de producto: capital por trabajador, tipo, etapa y Rauch. También los paneles de eventos. `WP_YEARS=2012-2018 WP_SCOPES=agro` |
| 9 | python/wp_agro_v4_est.py | Regresiones E1 a E7: asociación, localización y heterogeneidad. |
| 10 | stata/wp_agro_v4_event.do | Estudios de eventos E6: TWFE, Callaway y Sant'Anna, y Sun y Abraham. Argumento: `A` (celdas origen × producto) o `B` (origen × destino × producto). |
| 11 | stata/wp_agro_v4_ppml.do | PPML de E2e con `ppmlhdfe`. pyfixest no converge con esos efectos fijos. |
| 12 | python/wp_agro_v4_workbook.py | Workbook de la v4 en formato outreg2. |
| 13 | python/wp_agro_v4_exhibits.py, python/wp_agro_v4_paper.py | Tablas y figuras de la Note v4 y texto del paper. Argumentos de `wp_agro_v4_paper.py`: `desc`, `regs` o `flatten`. |
| **Ronda v5** | | |
| 14 | python/wp_agro_v5_data.py | Clases de producto de la v5: grupos de capital por trabajador según la fuente, escalera de umbrales, terciles, cortes agrupados y grado de procesamiento. |
| 15 | python/wp_agro_v5_data2.py | Agrega a esas clases el PCI del Atlas, la clasificación de Rauch completa, otras medidas de capital de EE.UU. y un chequeo por país. |
| 16 | python/wp_agro_v5_est.py, python/wp_agro_v5_est2.py | Regresiones E9, E10 y E12. Se pueden correr por bloques: `python wp_agro_v5_est.py e9a e10b ...` |
| 17 | python/wp_agro_v5_events.py | Paneles de eventos con las distintas definiciones de tratamiento (g_v4, g_ps y otras). |
| 18 | stata/wp_agro_v5_event.do | Estudios de eventos de la v5. Argumentos: parte (`A` o `B`) y bloque (std, fe, treat, treatps, het, het2, add, spill, placebo, csnev). |
| 19 | python/wp_agro_v5_match.py | Estudio de eventos apilado con controles emparejados por CEM. |
| 20 | python/wp_agro_v5_labels.py, python/wp_agro_v5_workbook.py | Etiquetas en palabras, el workbook y las figuras de la v5. |
| **Ronda v6** | | |
| 21 | python/wp_agro_v6_answers.py | Las 16 respuestas de definición de V6-01, cada una con el script y la línea de donde sale. |
| 22 | python/wp_agro_v6_data.py | V6-03 y V6-04: PCI a seis y a cuatro dígitos y ubicuidad en HS 2017 (OEC), PCI6 en HS 2012, Rauch binario y la marca hs_n1 de códigos sin correspondencia uno a uno. |
| 23 | python/wp_agro_v6_events.py | Paneles A (op), B (odp) y H (oh); stacks alineados por cohorte (A.7) y stacks placebo; tabla del universo (V6-10); marcas de los nuevos exportadores (V6-17). Tarda unos 10 minutos. |
| 24 | stata/wp_agro_v6_event.do | Estudios de eventos apilados y alineados. Argumentos: nivel (`A` o `B`) y bloque (main, cohort, placebo, chk, fe, het, hetplc, bridge). |
| 25 | python/wp_agro_v6_est.py | Regresiones V6-05 a V6-09, el lado de regresión de la tabla puente y la p de permutación de T2. Se puede correr por pasos: `pci`, `rauch`, `race`, `loc`, `cap` y `bridge`. |
| 26 | python/wp_agro_v6_workbook.py | Workbook de la v6: el de la v5, con las correcciones de V6-02, más las hojas 10.1 a 12.7, la tabla del conjunto primario y las figuras de la v6. |

## Qué datos lee

- **Base de aduanas emparejada:** `data/intermediate/wp/fdpy_base`, construida en Stata por `src/15_wp_extract_fdpy.do` en el repositorio. Es confidencial y no se comparte.
- **Archivos pequeños de `data/raw/`:** características de producto, concordancias HS, gravedad y aranceles.
- **Descargas públicas de `data/raw/external/` y `data/raw/unsd/`:**
  - tablas de correlación HS de UNSD;
  - Censo Agropecuario 2017 (USDA NASS) y NBER-CES, para el capital por trabajador;
  - clasificación de Rauch;
  - PCI del Atlas de Harvard y del OEC.

La especificación de cada ronda está en la raíz del repositorio: `especificaciones_estimaciones_v4_2026-11-17.md`, `..._v5_2026-11-24.md` y `..._v6_2026-11-25.md`. Los códigos V6-xx, E1 a E12 y T1 a T6 de esta tabla son los de esos documentos.
