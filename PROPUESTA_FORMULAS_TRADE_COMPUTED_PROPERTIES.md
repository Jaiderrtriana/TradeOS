# Propuesta — Fórmulas reales de las propiedades calculadas del Trade

Documento de revisión, **no código de dominio**. Todo lo extraído aquí
proviene literalmente de `legacy/Trading Journal v2.0 Stable.xlsx`, hoja
`📒 Trades`, vía el mismo venv aislado de `openpyxl` (`.venv` fuera del
proyecto, no es dependencia de `pyproject.toml`) ya usado y aprobado en
Sprints 2.1/3.1/3.2.

**Hallazgo relevante antes de las fórmulas:** el Excel real solo tiene **2
filas de trades reales** (`last_row_with_data = 3`, es decir filas 2 y 3 —
consistente con lo que `PROJECT_AUDIT.md` ya señalaba: *"bajo volumen de
trades actual"*). Ambas son `Long` y `SL` (perdedoras). No existe ningún
trade real `Short` ni ningún trade real `TP` en el archivo. Por eso, de
los 5 casos que pediste, **2 son filas reales verificadas exactamente
contra el Excel**, y **3 son casos calculados a mano usando la fórmula ya
confirmada** (nunca inventando una fórmula distinta) — cada uno
etiquetado explícitamente como tal, marcando qué parte es comportamiento
confirmado y cuál es necesaria para cubrir Short/TP/casos límite que el
Excel real no contiene.

**Funciones auxiliares / tablas ocultas / dependencias indirectas:**
ninguna. A diferencia de los motores de scoring (que usan rangos
nombrados como `W_CONF_BIAS`, tablas `VLOOKUP` como
`HTF_ALIGNMENT_SCORES`, etc.), las 5 fórmulas de este documento son
aritmética directa sobre celdas de la **misma fila** — sin `VLOOKUP`, sin
rango nombrado, sin hoja auxiliar. Confirmado leyendo las fórmulas
completas, no solo el resultado.

## Columnas involucradas (letra real → campo)

| Columna Excel | Nombre real | Campo propuesto |
|---|---|---|
| F | Dirección | `direction` |
| N | Entry Price | `entry_price` |
| O | SL | `stop_loss` |
| R | Exit price | `exit_price` |
| S | Resultado | `result` |
| AZ | Precio Mas Favorable | `mfe_price` |
| BA | Precio Menos Favorable | `mae_price` |
| X | R:R real | `r_multiple` |
| BB | MFE (R) | `mfe_r` |
| BC | MAE (R) | `mae_r` |
| BD | % Capturado | `captured_pct` |
| BE | Potencial Restante (R) | `potential_left_r` |

## 1. `r_multiple` (columna X, "R:R real")

**Fórmula real (fila 2):**
```
=IFERROR(IF(F2="Long",(R2-N2)/(N2-O2),(N2-R2)/(O2-N2)),"")
```

**Traducida:**
```
if direction == "long":
    r_multiple = (exit_price - entry_price) / (entry_price - stop_loss)
else:  # short
    r_multiple = (entry_price - exit_price) / (stop_loss - entry_price)
```
Envuelta en `IFERROR(...,"")` — si el cálculo falla (p. ej. división por
cero), el resultado es blanco, nunca un error visible. División por cero
no debería ocurrir en la práctica porque `INV-TRADE-01` ya exige
`entry_price ≠ stop_loss`.

**Lógica de negocio:** el resultado, expresado en múltiplos del riesgo
inicial (distancia Entry→Stop) — el estándar "R-multiple" de trading. Sin
`exit_price` (trade `Open`), no hay resultado que calcular.

**Estado:** ✅ comportamiento confirmado por el Excel, verificado
exactamente contra las 2 filas reales (ver Sección 6).

## 2. `mfe_r` (columna BB, "MFE (R)")

**Fórmula real:**
```
=IF(OR(AZ2="",N2="",O2=""),"",IF(F2="Long",(AZ2-N2)/ABS(N2-O2),(N2-AZ2)/ABS(N2-O2)))
```

**Traducida:**
```
if mfe_price is None or entry_price is None or stop_loss is None:
    mfe_r = None
elif direction == "long":
    mfe_r = (mfe_price - entry_price) / abs(entry_price - stop_loss)
else:  # short
    mfe_r = (entry_price - mfe_price) / abs(entry_price - stop_loss)
```

**Lógica de negocio:** cuánto llegó a favorecer el precio (el mejor precio
alcanzado durante la operación, `mfe_price`), en múltiplos de R —
independiente de dónde terminó realmente el trade.

**Estado:** ✅ comportamiento confirmado, verificado exactamente contra
las 2 filas reales.

## 3. `mae_r` (columna BC, "MAE (R)")

**Fórmula real:**
```
=IF(OR(BA2="",N2="",O2=""),"",IF(F2="Long",(N2-BA2)/ABS(N2-O2),(BA2-N2)/ABS(N2-O2)))
```

**Traducida:**
```
if mae_price is None or entry_price is None or stop_loss is None:
    mae_r = None
elif direction == "long":
    mae_r = (entry_price - mae_price) / abs(entry_price - stop_loss)
else:  # short
    mae_r = (mae_price - entry_price) / abs(entry_price - stop_loss)
```

**Lógica de negocio:** cuánto llegó a perjudicar el precio (el peor
precio alcanzado, `mae_price`), en múltiplos de R.

**Estado:** ✅ comportamiento confirmado, verificado exactamente contra
las 2 filas reales.

## 4. `captured_pct` (columna BD, "% Capturado")

**Fórmula real:**
```
=IF(OR(BB2="",BB2=0),"",IF(S2="TP",IFERROR(X2/BB2,""),"—"))
```

**Traducida:**
```
if mfe_r is None or mfe_r == 0:
    captured_pct = None            # blanco
elif result == "tp":
    captured_pct = r_multiple / mfe_r    # (IFERROR -> None si falla)
else:
    captured_pct = "—"             # texto literal, no numérico
```

**Lógica de negocio (BR-007, confirmada exactamente):** solo tiene
sentido en trades ganadores (`result = "tp"`). En cualquier otro caso
(perdedor, breakeven, o abierto) el Excel real no pone un número — pone
un guion largo (`—`, em dash) como marcador textual explícito de "no
aplica", **distinto** de una celda en blanco (que ocurre solo cuando
`mfe_r` es blanco o exactamente `0`).

**⚠️ Interpretación necesaria — decisión pendiente de tu aprobación:**

1. **Representación del "no aplica" en la API.** El Excel usa tres
   estados distintos: número (solo TP), texto `"—"` (no-TP con
   `mfe_r≠0`), y blanco (sin dato). Un campo JSON numérico no puede
   representar el string `"—"` de forma natural. Propongo colapsar
   `"—"` y blanco en un único `null` — consistente con cómo ya se
   representa "no aplica" en el resto de esta API (`published_at:
   null`, etc.) — pero es una decisión de representación, no de lógica
   de negocio, y quiero tu confirmación antes de codificarla.
2. **Escala del valor.** El `number_format` real de la columna BD en el
   Excel es `"General"` — **no** `"0%"`. Es decir, el valor crudo
   almacenado y usado por la fórmula es una **razón** (ej. `0.8`), no un
   porcentaje ya multiplicado por 100 (`80`). El nombre del campo
   (`captured_pct`, "% Capturado") sugiere visualmente un porcentaje,
   pero el Excel real nunca multiplica por 100. Necesito que confirmes
   si `captured_pct` debe devolver la razón cruda (`0.8`, fiel al
   Excel) o la versión ya escalada (`80.0`, más intuitiva para un
   consumidor de la API) — cualquiera de las dos es una interpretación,
   no algo que el Excel decida por sí solo, ya que el Excel nunca
   necesitó decidirlo (solo lo muestra sin formato).

**Estado:** ✅ regla de aplicabilidad y fórmula confirmadas exactamente;
⚠️ representación en la API (null vs `"—"`, razón vs porcentaje) requiere
tu decisión.

## 5. `potential_left_r` (columna BE, "Potencial Restante (R)")

**Fórmula real:**
```
=IF(BB2="","",BB2-MAX(0,IF(X2="",0,X2)))
```

**Traducida:**
```
if mfe_r is None:
    potential_left_r = None
else:
    potential_left_r = mfe_r - max(0, r_multiple if r_multiple is not None else 0)
```

**Lógica de negocio (BR-008, confirmada exactamente):** cuánto de la
mejor oportunidad (`mfe_r`) quedó "sobre la mesa" más allá de lo que el
trade realmente capturó — usando `MAX(0, r_multiple)` como base para no
"premiar" a un trade perdedor con un valor inflado (un `r_multiple`
negativo cuenta como `0` en la resta, no como un número negativo que
aumentaría el resultado).

**⚠️ Detalle real, no obvio, que vale la pena señalar explícitamente:**
la condición de blanco de esta fórmula es **`mfe_r == ""` (blanco
literal)**, **no** `mfe_r == 0` — a diferencia de `captured_pct`, que sí
trata `mfe_r == 0` como blanco. Es decir: si `mfe_r` es exactamente `0`
(el precio nunca se movió a favor), `potential_left_r` **sí calcula un
número real** (`0 - MAX(0, r_multiple)`), mientras que `captured_pct` da
blanco en ese mismo caso. Confirmado con el Caso 5 (Sección 6). Esto es
comportamiento real del Excel, no una inconsistencia mía — las dos
fórmulas simplemente no comparten la misma condición de "vacío".

**Otro detalle real:** la fórmula **no** aplica ningún piso al resultado
final — solo el término que se resta (`r_multiple`) pasa por `MAX(0,
...)`. Si `mfe_r` fuera, por inconsistencia de datos, menor que
`r_multiple` positivo, `potential_left_r` podría salir negativo. El
Excel no se protege contra esto; tampoco lo hago yo al traducir la
fórmula — sería inventar una validación que el Excel real no tiene.

**Estado:** ✅ comportamiento confirmado exactamente, incluyendo el
detalle de la condición de blanco distinta a `captured_pct`.

## 6. Los 5 casos de verificación

### Casos reales (extraídos del Excel, `data_only=True`, coinciden exactamente)

**Fila 2** — `direction=Long, entry_price=1788.48, stop_loss=1764.3, exit_price=1763.45, result=SL, mfe_price=1799.02, mae_price=1763.08`
| Campo | Valor real Excel | Fórmula aplicada a mano | Coincide |
|---|---|---|---|
| `r_multiple` | `-1.035153019` | `(1763.45-1788.48)/(1788.48-1764.3)` = `-1.035153...` | ✅ |
| `mfe_r` | `0.4358974359` | `(1799.02-1788.48)/24.18` = `0.435897...` | ✅ |
| `mae_r` | `1.050454921` | `(1788.48-1763.08)/24.18` = `1.050454...` | ✅ |
| `captured_pct` | `"—"` | `mfe_r≠0`, `result≠TP` → `"—"` | ✅ |
| `potential_left_r` | `0.4358974359` | `0.435897... - MAX(0,-1.035...)` = `0.435897...` | ✅ |

**Fila 3** — `direction=Long, entry_price=63069.8, stop_loss=62120.0, exit_price=62060.7, result=SL, mfe_price=64230.0, mae_price=62100.0`
| Campo | Valor real Excel | Fórmula aplicada a mano | Coincide |
|---|---|---|---|
| `r_multiple` | `-1.062434197` | `(62060.7-63069.8)/(63069.8-62120.0)` = `-1.062434...` | ✅ |
| `mfe_r` | `1.22152032` | `(64230.0-63069.8)/949.8` = `1.221520...` | ✅ |
| `mae_r` | `1.021057065` | `(63069.8-62100.0)/949.8` = `1.021057...` | ✅ |
| `captured_pct` | `"—"` | `mfe_r≠0`, `result≠TP` → `"—"` | ✅ |
| `potential_left_r` | `1.22152032` | `1.221520... - MAX(0,-1.062...)` = `1.221520...` | ✅ |

### Casos calculados a mano (el Excel real no tiene Short ni TP) — misma fórmula confirmada arriba, aplicada a números redondos elegidos para que la cuenta sea verificable a simple vista

**Caso 3 — Short, perdedor** — `direction=Short, entry_price=100, stop_loss=105, exit_price=102, result=sl, mfe_price=99, mae_price=104`
- `r_multiple = (100-102)/(105-100) = -0.4`
- `mfe_r = (100-99)/5 = 0.2`
- `mae_r = (104-100)/5 = 0.8`
- `captured_pct`: `mfe_r=0.2≠0`, `result≠tp` → `"—"` (→ `null` si aprobamas la Sección 4)
- `potential_left_r = 0.2 - MAX(0,-0.4) = 0.2`

**Caso 4 — Long, ganador (TP)** — único caso que ejercita la rama numérica de `captured_pct` — `direction=long, entry_price=100, stop_loss=95, exit_price=108, result=tp, mfe_price=110, mae_price=97`
- `r_multiple = (108-100)/(100-95) = 1.6`
- `mfe_r = (110-100)/5 = 2.0`
- `mae_r = (100-97)/5 = 0.6`
- `captured_pct = r_multiple / mfe_r = 1.6/2.0 = 0.8` (razón cruda; `80.0` si se escala — Sección 4)
- `potential_left_r = 2.0 - MAX(0,1.6) = 0.4`

**Caso 5 — Long, `mfe_r` exactamente 0 (caso límite)** — ilustra la diferencia de condición de blanco entre `captured_pct` y `potential_left_r` — `direction=long, entry_price=100, stop_loss=95, exit_price=90, result=sl, mfe_price=100 (nunca se movió a favor), mae_price=88`
- `r_multiple = (90-100)/(100-95) = -2.0`
- `mfe_r = (100-100)/5 = 0.0`
- `mae_r = (100-88)/5 = 2.4`
- `captured_pct`: `mfe_r==0` → blanco (`None`) — **no** se evalúa `result`
- `potential_left_r = 0.0 - MAX(0,-2.0) = 0.0` — **sí** da un número real, no blanco

## 7. Contradicciones con documentos congelados

**Ninguna encontrada.** Verificado explícitamente contra:
- `TRADEOS_DOMAIN_MODEL.md` DI-12 ("Captured % solo para TP, nunca negativo") — el Excel real nunca produce un número negativo para `captured_pct` (o es número solo-TP, o es `"—"`/blanco) ✅.
- `PROJECT_AUDIT.md` BR-007/BR-008 — ambas reglas coinciden exactamente con la fórmula real extraída ✅.
- `TRADEOS_DATABASE_DESIGN.md` §6.9 ("computed... never stored") — las 5 propiedades siguen sin columna propia; se calculan a partir de columnas que sí existen (`entry_price`, `stop_loss`, `exit_price`, `mfe_price`, `mae_price`, `direction`, `result`) ✅.

## 8. Resumen de decisiones pendientes

1. `captured_pct`: ¿colapsar `"—"` y blanco del Excel en un único `null` de la API? (recomendado)
2. `captured_pct`: ¿devolver la razón cruda (`0.8`, fiel al Excel) o el porcentaje escalado (`80.0`)?

Nada de esto se ha implementado. Ningún código de dominio ni seed fue
escrito — quedo a la espera de tu revisión antes de continuar con el
resto del análisis previo del Sprint 4.1 (flujo, transacción, Idempotency
-Key, patrón de factory Trading→Evaluation) y el plan de archivos.
