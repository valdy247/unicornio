# Bitácora de investigación — ZERO-01

**Pregunta:** ¿Cuándo conviene detectar cambios en un fotograma y procesar solo su región afectada, en lugar de aplicar el mismo filtro a todo el cuadro?

## Hipótesis

Si cambia una parte pequeña de una escena, la actualización localizada podría ahorrar tiempo. La detección de diferencias también tiene costo y puede superar ese ahorro.

## Diseño

- Entrada inicial: 60 fotogramas sintéticos de 960 × 540 píxeles; fondo fijo y rectángulo móvil.
- Base de comparación: `cv2.GaussianBlur` sobre cada cuadro completo, kernel de 15 × 15.
- Alternativa: detección de diferencias completa en CPU + región rectangular de cambios + dos márgenes de contexto + actualización del resultado anterior.
- Se mide tiempo con `perf_counter`, separado por método, **incluyendo detección de cambios**; se comprueba igualdad exacta de píxeles.
- El primer fotograma debe procesarse completo en ambas variantes.

## Observación preliminar (máquina de desarrollo, NO el PC del usuario)

En una ejecución local: 60 fotogramas, **~1.96×** más rápido que recalcular todo; error máximo de píxel **0**. Cinco pruebas automáticas pasaron. La velocidad puede variar por equipo, carga, escena y versión de OpenCV. **Este dato no demuestra novedad científica ni mejora universal.**

## Lo que aprendimos

1. Actualizar solo los píxeles cambiados es incorrecto con filtros espaciales; la modificación influye en píxeles vecinos.
2. El cálculo localizado requiere margen para los píxeles de salida afectados y margen adicional para el contexto de entrada.
3. Detectar cambios mediante operaciones vectorizadas de OpenCV resultó mucho más rápido en esta prueba que usar `np.nonzero` sobre todo el fotograma.
4. Si cambia gran parte del cuadro, se usa el cálculo completo.

## Próximos experimentos

- Repetir con videos reales de cámara fija y cámara en movimiento.
- Medir memoria, consumo energético y escalabilidad según resolución.
- Comparar contra métodos estándar de seguimiento de regiones, bloques y caché (buscar literatura y patentes antes de reclamar originalidad).
- Formular una hipótesis diferente si solo reproducimos técnicas conocidas.
