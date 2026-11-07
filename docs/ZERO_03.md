# ZERO-03 — Detección preliminar adaptativa

## Motivación

En el equipo del usuario, ZERO-02 obtuvo: **static 1.45×**, **camera 0.36×**, **global 0.34×**, con error máximo de píxel cero y 10 pruebas correctas. Cuando cambia todo el fotograma, buscar todos los píxeles modificados cuesta tiempo sin ahorrar el filtro posterior.

## Hipótesis y algoritmo

Antes de la detección completa de diferencias, comparar una **rejilla dispersa** de píxeles de dos fotogramas:

- Si más del 20% de las posiciones muestreadas difieren, aplicar directamente el desenfoque completo.
- En caso contrario, utilizar la detección exhaustiva y la actualización regional de ZERO-01.
- **Nunca** omitir la detección completa basándonos solo en una muestra pequeña. Incluso si la muestra no detecta un cambio, la actualización regional todavía lo detecta. Así mantenemos igualdad exacta frente al filtro completo.

Esto es una *estrategia heurística conocida*, no una innovación original demostrada. Puede ser peor en imágenes estáticas por el costo adicional del muestreo.

## Ejecutar (PowerShell)

Desde el repositorio actualizado:

```powershell
git pull
python -m unittest discover -s tests -v
python zero_03.py
```

También se admite video propio, sin subirlo al repositorio:

```powershell
python zero_03.py --scenario video --video "C:\Videos\prueba.mp4"
```

Archivo de resultados: `results/zero_03.json`.

## Qué medimos

Para cada escenario se miden los tiempos de tres métodos, con el mismo video y una sola CPU (el número de hilos de OpenCV se fija en 1):

1. **full:** desenfoque de todos los píxeles.
2. **zero_02:** detección exhaustiva y actualización regional.
3. **adaptive:** muestreo previo con salida anticipada cuando los cambios son globales.

Se utilizan medianas de varias repeticiones. Se comprueba igualdad exacta de la salida del filtro, fotograma a fotograma. No se mide consumo eléctrico, generación de video con IA, lectura del archivo ni decodificación.

## Lo que NO demuestra

- No prueba que la generación de video con IA sea más barata.
- No demuestra reducción de energía.
- No demuestra una nueva técnica; la ganancia depende de la escena y el hardware.
- Los métodos existentes de detección de movimiento y estimación de cámara siguen siendo posibles alternativas que habrá que investigar.
