# ZERO-04 — Reutilización bajo movimiento de cámara conocido

## Por qué este experimento

Los resultados aportados por el usuario para ZERO-03 son:

| Escenario | ZERO-02 | ZERO-03 |
| --- | ---: | ---: |
| Cámara fija | 1.34× | 1.28× |
| Cámara móvil | 0.35× | 0.98× |
| Cambios globales | 0.35× | 1.00× |

Todas las 15 pruebas pasaron. El próximo problema es **reutilizar resultados aunque se traslade la escena completa**, no solo decidir cuándo procesarla íntegramente.

## Hipótesis

Si conocemos exactamente el desplazamiento horizontal y vertical entre dos fotogramas, podemos desplazar el resultado previo, identificar cambios adicionales y recomputar solo bloques afectados. Como se reutiliza una operación cara —aquí, `cv2.bilateralFilter`—, quizás ahorremos procesamiento.

Este algoritmo utiliza técnicas ya conocidas, **no es una invención verificada**.

## Limitación crítica: cámara conocida de antemano

El movimiento de cámara es **un desplazamiento entero proporcionado por el generador de escenas sintéticas**. No lo calculamos desde imágenes reales. Este experimento es una *cota optimista* sobre el posible beneficio de reutilización: un futuro sistema necesitaría medir cuánto cuesta detectar movimiento y manejar movimientos no translacionales (giros, perspectiva, objetos a diferentes profundidades). No sería apropiado presentar estos números como rendimiento en videos reales.

`np.roll` simula movimiento circular, por lo que el contenido reaparece al otro extremo del fotograma. Esto **no modela por completo una cámara real**; se utiliza para aislar el problema de reutilización y corrección de bordes.

## Qué mide

- Filtrado bilateral completo de cada fotograma.
- Reutilización del resultado filtrado anterior usando traslación conocida, detección de diferencias, corrección por bloques y fallback cuando hay demasiados cambios.
- Comparación píxel a píxel frente al filtrado completo: error máximo debe ser cero.
- Tiempos de CPU con OpenCV limitado a un hilo, medianas de repeticiones.
- No mide electricidad, videos generados con IA, costes de nube, ni cálculo de movimiento.

## Ejecutar en Windows PowerShell

Desde `C:\Users\valdy\unicornio\unicornio-labs-github`:

```powershell
git pull
python -m unittest discover -s tests -v
python zero_04.py
```

Se guardará `results/zero_04.json`.

## Aprendizaje preliminar (máquina de desarrollo, NO la del usuario)

Una prueba local con 960×540 píxeles, 20–35 fotogramas y 1–2 repeticiones sugirió lo siguiente:

- **Filtro gaussiano barato:** la reutilización resulta más lenta que procesar toda la imagen.
- **Filtro bilateral más caro:** en desplazamiento conocido puede ser alrededor de 1.7× más rápida con objeto móvil, pero no siempre conviene en cambios globales.
- La ventaja desaparece si agregamos un detector de movimiento costoso, si muchos bloques cambian o si el contenido no se ajusta al supuesto de traslación.

La verdadera pregunta para una investigación posterior es si podremos **estimar la transformación a menor costo que el ahorro computacional generado**. No hay evidencia todavía de una mejora general.

## Próximas hipótesis

1. Medir un detector real de movimiento (con costo incluido), frente a la cota optimista anterior.
2. Probar escenas con movimiento no circular y nuevos píxeles expuestos por la cámara.
3. Medir diferentes tamaños de bloque y frecuencia de actualizaciones.
4. Buscar técnicas previas de movimiento óptico, compensación de movimiento y cachés de renderizado antes de plantear novedad científica.
