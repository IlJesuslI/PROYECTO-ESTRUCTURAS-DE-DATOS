"""Benchmark simple de FoodQueue con persistencia real JSON.

Ejemplo:
    python benchmark.py 1000

Mide el costo acumulado de crear pedidos incluyendo guardado en disco.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from app.service import FoodQueueService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("orders", type=int, nargs="?", default=1000)
    args = parser.parse_args()
    if not 1 <= args.orders <= 100_000:
        raise SystemExit("Use un valor entre 1 y 100000.")

    with tempfile.TemporaryDirectory() as directory:
        state_path = Path(directory) / "state.json"
        service = FoodQueueService(state_path)
        product = service.list_products()[0]

        start = time.perf_counter()
        for index in range(args.orders):
            service.create_order(
                {
                    "customer": f"Benchmark {index}",
                    "priority": 2 if index % 10 == 0 else 0,
                    "items": [{"product_id": product["id"], "quantity": 1}],
                }
            )
        elapsed = time.perf_counter() - start
        size_kib = state_path.stat().st_size / 1024

        print(f"Pedidos: {args.orders}")
        print(f"Tiempo total: {elapsed:.3f} s")
        print(f"Promedio: {elapsed / args.orders * 1000:.3f} ms/pedido")
        print(f"Archivo JSON: {size_kib:.1f} KiB")
        print("Nota: los resultados dependen de CPU, disco, sistema operativo y carga del equipo.")


if __name__ == "__main__":
    main()
