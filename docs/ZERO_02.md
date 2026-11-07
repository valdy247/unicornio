# ZERO-02 — ¿Cuándo deja de compensar procesar solo lo que cambia?

## Objetivo

Comparar el algoritmo incremental de ZERO-01 frente a un desenfoque completo con tres escenarios reproducibles en CPU, y luego con un video real.

## Casos

1. **static**: fondo fijo, objeto moviéndose. La región afectada suele ser pequeña.
2. **camera**: desplazamiento global sintético. Se modifican casi todos los píxeles.
3. **global**: variación global de brillo. La detección debería descubrir cambios extensos.
4. **video**: video personal opcional, procesado localmente. El video **no** se sube a GitHub.

## Comandos (PowerShell)

Desde la carpeta clonada del repositorio:

```powershell
git pull
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe zero_02.py
```

Con un video que grabes tú mismo, usa por ejemplo:

```powershell
.\.venv\Scripts\python.exe zero_02.py --scenario video --video "C:\Videos\prueba.mp4" --frames 60
```

El resultado se guarda en `results/zero_02.json`.

## Interpretación

- `speedup > 1`: incremental más rápido para esa ejecución.
- `speedup < 1`: incremental más lento para esa ejecución.
- `average_changed_bbox_percent`: área de la **caja rectangular** que rodea las diferencias, no porcentaje exacto de píxeles cambiados.
- `max_pixel_error = 0`: salida idéntica frente al desenfoque completo.
- Los tiempos son medianas de **tres pasadas** por defecto.
- Se excluye la decodificación y el redimensionamiento de video, pero se incluye el coste de detectar cambios.
- No se mide energía, GPU ni velocidad de generación de video con IA.

## Hipótesis refutable

El procesamiento regional puede ganar cuando los cambios son pequeños, pero perder cuando la detección global resulta más costosa que aplicar directamente el desenfoque completo.

**No existe todavía un algoritmo nuevo.** ZERO-02 aporta evidencia sobre el límite de una técnica existente. Antes de reclamar originalidad hay que investigar bibliografía y patentes.

## Registro inicial

En una prueba sintética local de 15 cuadros a 320 × 180, una sola pasada (datos **no** obtenidos del equipo del usuario):

| Escenario | Velocidad relativa |
| --- | --- |
| static | 1.32× |
| camera | 0.67× |
| global | 0.68× |

Son cifras exploratorias: el rendimiento depende de resolución, hardware, versión de bibliotecas y número de pasadas. No representan resultados garantizados.
