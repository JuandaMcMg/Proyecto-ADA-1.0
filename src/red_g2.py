#!/usr/bin/env python3
"""Solución base explicada para el proyecto ADAG, Grupo 2: Red."""

import argparse
import heapq
import itertools
import json
import math
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Leer y comprobar los datos
# ---------------------------------------------------------------------------


def cargar_instancia(ruta_archivo: Path) -> dict[str, Any]:
    """Lee el JSON y comprueba que sus datos básicos sean válidos."""
    with ruta_archivo.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)

    claves_necesarias = {"parametros", "nodos", "grafo"}
    if not claves_necesarias.issubset(datos):
        raise ValueError(
            f"Al JSON le faltan estas secciones: {sorted(claves_necesarias)}"
        )

    parametros = datos["parametros"]
    nodos = datos["nodos"]

    if parametros["numero_nodos"] != len(nodos):
        raise ValueError(
            "El número indicado en 'numero_nodos' no coincide con la lista."
        )
    if not nodos:
        raise ValueError("La lista de nodos está vacía.")

    identificadores = [nodo["id"] for nodo in nodos]
    if len(identificadores) != len(set(identificadores)):
        raise ValueError("Cada nodo debe tener un identificador diferente.")

    identificadores_validos = set(identificadores)
    parejas_vistas = set()

    for nodo in nodos:
        if nodo["coeficiente_utilidad"] < 0:
            raise ValueError(
                f"El coeficiente de {nodo['id']} no puede ser negativo."
            )
        if nodo["presupuesto_total_nodo"] < 0:
            raise ValueError(
                f"El presupuesto de {nodo['id']} no puede ser negativo."
            )
        if nodo["costo_participacion"] < 0:
            raise ValueError(f"El costo de {nodo['id']} no puede ser negativo.")

    for arista in datos["grafo"]:
        nodo_a = arista["u"]
        nodo_b = arista["v"]
        peso = arista["peso_influencia"]

        if (
            nodo_a not in identificadores_validos
            or nodo_b not in identificadores_validos
        ):
            raise ValueError(
                f"La relación {nodo_a}-{nodo_b} menciona un nodo inexistente."
            )
        if nodo_a == nodo_b:
            raise ValueError(
                f"No se permiten relaciones de un nodo consigo mismo: {nodo_a}."
            )
        if not 0 <= peso <= 1:
            raise ValueError(f"El peso de {nodo_a}-{nodo_b} debe estar entre 0 y 1.")

        pareja = frozenset((nodo_a, nodo_b))
        if pareja in parejas_vistas:
            raise ValueError(f"La relación {nodo_a}-{nodo_b} está repetida.")
        parejas_vistas.add(pareja)

    return datos


def crear_mapa_de_influencias(datos: dict[str, Any]) -> dict[frozenset[str], float]:
    """Permite consultar rápidamente el peso entre dos nodos."""
    return {
        # frozenset hace que N01-N02 y N02-N01 sean la misma pareja.
        frozenset((arista["u"], arista["v"])): arista["peso_influencia"]
        for arista in datos["grafo"]
    }


# ---------------------------------------------------------------------------
# 2. Medir la utilidad y elegir participantes
# ---------------------------------------------------------------------------


def calcular_utilidad_del_grupo(
    grupo: tuple[dict[str, Any], ...],
    todos_los_nodos: list[dict[str, Any]],
    influencias: dict[frozenset[str], float],
) -> float:
    """
    Calcula la utilidad según el modelo provisional explicado en el informe.

    Cada nodo objetivo recibe influencia de los participantes elegidos.
    Su aporte no supera su coeficiente de utilidad (la utilidad se satura).
    """
    utilidad_total = 0.0

    for nodo_objetivo in todos_los_nodos:
        influencia_recibida = 0.0

        for participante in grupo:
            if participante["id"] == nodo_objetivo["id"]:
                # Un nodo cuenta como influencia propia igual a 1.
                influencia_recibida += 1.0
            else:
                pareja = frozenset((participante["id"], nodo_objetivo["id"]))
                influencia_recibida += influencias.get(pareja, 0.0)

        # La influencia total de un objetivo no puede aportar más de 1.
        influencia_limitada = min(1.0, influencia_recibida)
        utilidad_total += (
            nodo_objetivo["coeficiente_utilidad"] * influencia_limitada
        )

    return utilidad_total


def elegir_participantes(
    datos: dict[str, Any],
) -> dict[str, Any]:
    """
    Prueba todos los grupos posibles y devuelve el grupo factible de mayor utilidad.

    Es una búsqueda exacta apropiada para el caso pequeño de 15 nodos.
    """
    parametros = datos["parametros"]
    nodos = datos["nodos"]
    cupo = parametros["cupo_participantes_por_ronda_k"]
    presupuesto_de_costos = parametros["presupuesto_costos_participacion_por_ronda"]

    if not 0 <= cupo <= len(nodos):
        raise ValueError("El cupo debe estar entre 0 y el número de nodos.")

    influencias = crear_mapa_de_influencias(datos)
    mejor_grupo = None
    mejor_utilidad = -math.inf
    grupos_que_mejoran = []
    cantidad_factible = 0
    cantidad_total = math.comb(len(nodos), cupo)

    # combinations genera cada grupo de 'cupo' nodos una sola vez.
    for grupo_candidato in itertools.combinations(nodos, cupo):
        costo_del_grupo = sum(
            nodo["costo_participacion"] for nodo in grupo_candidato
        )

        # Un grupo que excede el presupuesto no puede ser una respuesta válida.
        if costo_del_grupo > presupuesto_de_costos:
            continue

        cantidad_factible += 1
        utilidad = calcular_utilidad_del_grupo(
            grupo_candidato, nodos, influencias
        )
        ids_candidatos = tuple(nodo["id"] for nodo in grupo_candidato)
        ids_mejor_grupo = (
            tuple(nodo["id"] for nodo in mejor_grupo)
            if mejor_grupo is not None
            else None
        )

        # Si hay empate, se elige el grupo con identificadores alfabéticamente menor.
        mejora_la_mejor = utilidad > mejor_utilidad + 1e-12
        gana_el_empate = (
            abs(utilidad - mejor_utilidad) <= 1e-12
            and (ids_mejor_grupo is None or ids_candidatos < ids_mejor_grupo)
        )

        if mejora_la_mejor or gana_el_empate:
            mejor_grupo = grupo_candidato
            mejor_utilidad = utilidad
            grupos_que_mejoran.append(
                {
                    "nuevas_mejoras": list(ids_candidatos),
                    "costo": costo_del_grupo,
                    "utilidad": round(utilidad, 6),
                }
            )

    if mejor_grupo is None:
        raise ValueError(
            "No hay un grupo que cumpla a la vez el cupo y el presupuesto de costos."
        )

    # Calcula cuánto aumentaría la utilidad al añadir cada integrante del grupo.
    traza_de_ganancias = []
    grupo_parcial = ()
    utilidad_anterior = 0.0

    for nodo in mejor_grupo:
        grupo_parcial = (*grupo_parcial, nodo)
        utilidad_actual = calcular_utilidad_del_grupo(
            grupo_parcial, nodos, influencias
        )
        traza_de_ganancias.append(
            {
                "nodo_agregado": nodo["id"],
                "utilidad_antes": round(utilidad_anterior, 6),
                "utilidad_despues": round(utilidad_actual, 6),
                "ganancia_marginal": round(utilidad_actual - utilidad_anterior, 6),
            }
        )
        utilidad_anterior = utilidad_actual

    resumen_de_busqueda = [
        {
            "grupos_totales": cantidad_total,
            "grupos_factibles_evaluados": cantidad_factible,
        }
    ]

    return {
        "grupo": mejor_grupo,
        "utilidad": mejor_utilidad,
        "traza_busqueda": resumen_de_busqueda + grupos_que_mejoran,
        "ganancias_marginales": traza_de_ganancias,
        "cantidad_de_grupos": cantidad_total,
    }


# ---------------------------------------------------------------------------
# 3. Repartir el presupuesto
# ---------------------------------------------------------------------------


def calcular_ganancia_de_una_unidad(
    nodo: dict[str, Any], unidades_ya_asignadas: int
) -> float:
    """Calcula la utilidad adicional de dar una unidad más a un nodo."""
    coeficiente = nodo["coeficiente_utilidad"]

    # La fórmula corresponde a u(x) = coeficiente * ln(1 + x).
    # La resta da la utilidad de la siguiente unidad.
    return coeficiente * math.log(
        (unidades_ya_asignadas + 2) / (unidades_ya_asignadas + 1)
    )


def repartir_presupuesto(
    grupo: tuple[dict[str, Any], ...],
    presupuesto_por_ronda: int,
    cantidad_de_rondas: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Asigna unidades enteras, siempre al nodo con mayor ganancia marginal.

    Una cola de prioridad (montículo) mantiene arriba la próxima unidad más
    provechosa. Python ofrece un montículo mínimo, así que guardamos la ganancia
    con signo negativo para que la ganancia mayor salga primero.
    """
    unidades_acumuladas = {nodo["id"]: 0 for nodo in grupo}
    resultados_por_ronda = []

    for numero_de_ronda in range(1, cantidad_de_rondas + 1):
        asignacion_de_la_ronda = {nodo["id"]: 0 for nodo in grupo}
        traza_de_la_ronda = []

        # Cada elemento de la cola tiene: prioridad, ID del nodo y nodo.
        cola_de_prioridad = []
        for nodo in grupo:
            if unidades_acumuladas[nodo["id"]] < nodo["presupuesto_total_nodo"]:
                ganancia = calcular_ganancia_de_una_unidad(
                    nodo, unidades_acumuladas[nodo["id"]]
                )
                heapq.heappush(
                    cola_de_prioridad,
                    (-ganancia, nodo["id"], nodo),
                )

        # Reparte el presupuesto de esta ronda, una unidad a la vez.
        for numero_de_unidad in range(1, presupuesto_por_ronda + 1):
            if not cola_de_prioridad:
                break  # Todos los nodos llegaron a su límite individual.

            ganancia_negativa, _, nodo_elegido = heapq.heappop(cola_de_prioridad)
            ganancia = -ganancia_negativa
            id_nodo = nodo_elegido["id"]

            unidades_acumuladas[id_nodo] += 1
            asignacion_de_la_ronda[id_nodo] += 1
            traza_de_la_ronda.append(
                {
                    "unidad": numero_de_unidad,
                    "nodo": id_nodo,
                    "ganancia_marginal": round(ganancia, 6),
                    "asignado_acumulado": unidades_acumuladas[id_nodo],
                }
            )

            # Si aún le queda capacidad, ponemos su próxima ganancia en la cola.
            if unidades_acumuladas[id_nodo] < nodo_elegido["presupuesto_total_nodo"]:
                nueva_ganancia = calcular_ganancia_de_una_unidad(
                    nodo_elegido, unidades_acumuladas[id_nodo]
                )
                heapq.heappush(
                    cola_de_prioridad,
                    (-nueva_ganancia, id_nodo, nodo_elegido),
                )

        resultados_por_ronda.append(
            {
                "ronda": numero_de_ronda,
                "asignacion": asignacion_de_la_ronda,
                "unidades_repartidas": sum(asignacion_de_la_ronda.values()),
                "traza_ganancias_marginales": traza_de_la_ronda,
            }
        )

    return resultados_por_ronda, unidades_acumuladas


# ---------------------------------------------------------------------------
# 4. Ejecutar el proceso completo y comprobar restricciones
# ---------------------------------------------------------------------------


def resolver_instancia(ruta_archivo: Path) -> dict[str, Any]:
    """Resuelve el caso, mide el tiempo y prepara el reporte final."""
    datos = cargar_instancia(ruta_archivo)
    inicio = time.perf_counter()

    seleccion = elegir_participantes(datos)
    grupo_elegido = seleccion["grupo"]
    parametros = datos["parametros"]
    asignaciones, unidades_acumuladas = repartir_presupuesto(
        grupo_elegido,
        parametros["presupuesto_ruido_por_ronda_B"],
        parametros["numero_rondas"],
    )
    tiempo_transcurrido = time.perf_counter() - inicio

    costo_del_grupo = sum(
        nodo["costo_participacion"] for nodo in grupo_elegido
    )
    todos_respetan_su_limite = all(
        unidades_acumuladas[nodo["id"]] <= nodo["presupuesto_total_nodo"]
        for nodo in grupo_elegido
    )

    return {
        "instancia": ruta_archivo.name,
        "supuestos_modelado": [
            "La red es no dirigida porque cada pareja aparece una sola vez.",
            "La utilidad de selección es cobertura ponderada saturada: "
            "F(S)=sum_v a_v*min(1, suma de influencias de S hacia v), "
            "con influencia propia igual a 1.",
            "La selección se optimiza exactamente para el caso recibido, "
            "sujeta al cupo k y al costo máximo por ronda.",
            "La utilidad de reparto es u_i(x)=a_i*ln(1+x); las unidades "
            "son enteras y la ganancia marginal disminuye.",
            "Se usa el mismo grupo en todas las rondas y no se simulan fallas, "
            "porque el JSON no contiene estados ni probabilidades de falla.",
            "El presupuesto total por nodo se interpreta como límite acumulado "
            "entre rondas.",
            "Las utilidades y la interacción del grafo son una formalización "
            "provisional, no una fórmula confirmada por la profesora.",
        ],
        "resultado": {
            "nodos_seleccionados": [nodo["id"] for nodo in grupo_elegido],
            "costo_participacion_del_grupo": costo_del_grupo,
            "limite_costo_por_ronda": parametros[
                "presupuesto_costos_participacion_por_ronda"
            ],
            "utilidad_de_seleccion": round(seleccion["utilidad"], 6),
            "busqueda_seleccion": "enumeración exacta de grupos factibles",
            "asignaciones_por_ronda": asignaciones,
            "uso_acumulado_por_nodo": unidades_acumuladas,
            "restricciones": {
                "cupo_cumplido": len(grupo_elegido)
                == parametros["cupo_participantes_por_ronda_k"],
                "costo_cumplido": costo_del_grupo
                <= parametros["presupuesto_costos_participacion_por_ronda"],
                "presupuesto_ruido_por_ronda_cumplido": all(
                    ronda["unidades_repartidas"]
                    <= parametros["presupuesto_ruido_por_ronda_B"]
                    for ronda in asignaciones
                ),
                "limite_total_por_nodo_cumplido": todos_respetan_su_limite,
            },
            "traza_seleccion": seleccion["traza_busqueda"],
            "traza_ganancias_marginales_seleccion": seleccion[
                "ganancias_marginales"
            ],
            "combinaciones_posibles": seleccion["cantidad_de_grupos"],
            "tiempo_ejecucion_segundos": round(tiempo_transcurrido, 6),
        },
    }


# ---------------------------------------------------------------------------
# 5. Leer opciones de ejecución y guardar el resultado
# ---------------------------------------------------------------------------


def main() -> None:
    """Permite ejecutar el programa desde la terminal."""
    directorio_proyecto = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Solución base provisional para el Grupo 2: Red."
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        type=Path,
        default=directorio_proyecto / "data" / "entrada_G2_red_15_nodos.json",
        help="Archivo JSON de entrada.",
    )
    parser.add_argument(
        "-o",
        "--salida",
        type=Path,
        default=directorio_proyecto / "resultados" / "resultado_G2.json",
        help="Archivo donde guardar los resultados.",
    )
    opciones = parser.parse_args()

    resultado = resolver_instancia(opciones.archivo)
    texto_resultado = json.dumps(resultado, ensure_ascii=False, indent=2)
    opciones.salida.parent.mkdir(parents=True, exist_ok=True)
    opciones.salida.write_text(texto_resultado + "\n", encoding="utf-8")

    print(texto_resultado)
    print(f"\nResultado guardado en: {opciones.salida}")


if __name__ == "__main__":
    main()
