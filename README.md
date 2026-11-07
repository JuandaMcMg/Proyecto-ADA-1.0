# Proyecto ADAG Grupo 2 — Red

Solución base reproducible en Python para el caso de prueba del Grupo 2.

## Estructura

```text
.
├── data/
│   └── entrada_G2_red_15_nodos.json
├── resultados/
│   └── resultado_G2.json
├── src/
│   └── red_g2.py
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.10 o posterior.
- No requiere paquetes externos.

## Ejecución

Desde la carpeta raíz del proyecto:

```powershell
python src\red_g2.py
```

Por defecto, el programa lee la instancia de `data/` y guarda la salida en
`resultados/`. También se pueden especificar otras rutas:

```powershell
python src\red_g2.py data\entrada_G2_red_15_nodos.json --salida resultados\resultado_G2.json
```

El programa imprime y guarda un JSON con los participantes seleccionados, el
costo, la utilidad según el modelo provisional, las asignaciones por ronda,
las ganancias marginales y la verificación de restricciones.

## Alcance y supuestos

El enunciado y el archivo de entrada no especifican una función numérica de
utilidad, cómo se traducen los pesos del grafo en utilidad, ni cómo ocurren las
fallas. Por eso el programa declara explícitamente un modelo provisional:

- utilidad de selección por cobertura ponderada y saturada;
- selección exacta para la instancia pequeña, respetando cupo y presupuesto de
  costos;
- utilidad de reparto `u_i(x) = a_i ln(1+x)`, con unidades enteras y límites
  acumulados por nodo;
- mismo grupo en las rondas y sin fallas simuladas.

Estos supuestos sirven para ejecutar y verificar la solución base; deben
reemplazarse si la profesora entrega fórmulas o reglas distintas. El reporte
incluye dichos supuestos para no confundirlos con datos oficiales.
