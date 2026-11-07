# Unicornio Labs 🔬

Laboratorio experimental de **Unicornio Academy**, independiente del producto principal. Investigamos métodos de computación que reduzcan el costo de crear y transformar contenido digital. **No afirmamos que nuestras técnicas sean invenciones nuevas**: primero medimos y comparamos.

## ZERO-01: actualización parcial de imágenes

Experimento de referencia en CPU: comparar un desenfoque gaussiano del fotograma completo contra uno que detecta cambios y recalcula solo la región afectada, incluyendo el margen necesario para que el resultado sea idéntico al original.

### Requisitos

- Windows, macOS o Linux; Python 3.11 o superior.
- Sin GPU dedicada; compatible con Intel UHD y 16 GB de RAM.

### Instalación en PowerShell (Windows)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> Si ya activaste `.venv`, también puedes usar `python` en vez de `.\.venv\Scripts\python.exe`.

### Ejecutar

```powershell
.\.venv\Scripts\python.exe zero_01.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para usar tu propio video, con la cámara quieta si es posible:

```powershell
.\.venv\Scripts\python.exe zero_01.py --video "C:\ruta\al\video.mp4" --frames 60
```

Las dos imágenes finales se guardarán en `results/`, que **no** se sube a GitHub.

### Qué significa el resultado

- `Factor de velocidad > 1x`: el método incremental fue más rápido en esa ejecución.
- `< 1x`: el método incremental fue más lento. **Ambos son resultados válidos**.
- `Error máximo de píxel = 0`: ambos métodos producen el mismo resultado digital en esa ejecución.
- El tiempo incremental **incluye** detectar cambios en toda la imagen.
- El procesamiento de video real puede ser más lento si se mueve la cámara o cambian muchos píxeles.
- Los tiempos no incluyen leer/decomprimir el video ni escribir las imágenes, porque son compartidos por ambos métodos.

**Importante:** procesar solo las regiones modificadas es una técnica conocida. ZERO-01 sirve para establecer una referencia verificable, no es una patente ni prueba de novedad. Véase [registro de investigación](docs/RESEARCH_LOG.md).


## ZERO-02: límites del procesamiento incremental

Comparamos tres situaciones: un objeto moviéndose con la cámara quieta, movimiento global de cámara y cambios de brillo en toda la escena. Incluye tres repeticiones y guarda los resultados en un archivo JSON.

En PowerShell, desde la carpeta clonada:

```powershell
git pull
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe zero_02.py
```

Prueba opcional con un video propio:

```powershell
.\.venv\Scripts\python.exe zero_02.py --scenario video --video "C:\Videos\prueba.mp4"
```

Lee las explicaciones, limitaciones y resultados en [ZERO-02](docs/ZERO_02.md).

**No confundir:** esta prueba mide el costo de un filtro de desenfoque, no la generación de video con IA. Una aceleración en este experimento no implica la misma mejora en modelos generativos.


## ZERO-03: clasificación rápida para evitar trabajo inútil

Nuevo experimento CPU: muestreo ligero para decidir cuándo conviene calcular el fotograma completo y cuándo intentar la actualización regional.

```powershell
git pull
python -m unittest discover -s tests -v
python zero_03.py
```

Compara `full`, `zero_02` y `adaptive`, y guarda los tiempos en `results/zero_03.json`.

Detalles: [ZERO-03](docs/ZERO_03.md). No es una técnica original demostrada, sino otra referencia necesaria para una futura investigación.


## ZERO-04: reutilizar cálculos con movimiento conocido (experimento controlado)

Este nuevo experimento compara un filtrado bilateral completo con la reutilización por bloques cuando el **desplazamiento de cámara ya es conocido**. Es una prueba optimista sobre movimiento sintético, **no** una solución a la estimación de movimiento real.

```powershell
git pull
python -m unittest discover -s tests -v
python zero_04.py
```

Informe: `results/zero_04.json`. Metodología y límites: [ZERO-04](docs/ZERO_04.md).


---

## ✨ ORBIT Studio — Experimento de interacción 3D

Prototipo de editor de video local: letras 3D arrastrables, detección corporal con MediaPipe, oclusión básica y rebote visual al estimar contacto con los pies. También incluye una simulación manual y exportación WebM sin audio.

**[Abrir las instrucciones de ORBIT-01](orbit/README.md)** · **[Ver el editor](orbit/index.html)**

Para ejecutar la página localmente desde la raíz del repositorio:

```powershell
python -m http.server 8000
```

Después abre `http://localhost:8000/orbit/` en Chrome o Edge. Hay limitaciones conocidas: profundidad no reconstruida, cámara no anclada y contacto heurístico, no físico.
