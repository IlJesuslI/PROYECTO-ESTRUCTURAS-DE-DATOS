"""Benchmark repetible: registro masivo y extracción individual con SQLite.

Uso: python benchmark.py 100000
La duración en Windows puede ser diferente a otros sistemas.
"""
import argparse
import tempfile
import time
from pathlib import Path

from app.service import FoodQueueService


def main():
    parser = argparse.ArgumentParser(description='Benchmark FoodQueue con arreglos de prioridad')
    parser.add_argument('orders', type=int, nargs='?', default=1000)
    args = parser.parse_args()
    if not 1 <= args.orders <= 100_000:
        parser.error('Indique una cantidad entre 1 y 100000.')
    with tempfile.TemporaryDirectory() as directory:
        service = FoodQueueService(Path(directory)/'state.json')
        product = service.list_products()[0]
        started = time.perf_counter()
        for i in range(args.orders):
            service.create_order({'customer':f'Prueba {i}', 'priority':int(i%7==0),
                                  'items':[{'product_id':product['id'],'quantity':1}]})
        elapsed = time.perf_counter()-started
        started = time.perf_counter()
        record = service.process_next_order()
        process_ms = (time.perf_counter()-started)*1000
        started = time.perf_counter()
        status = service.status()
        status_ms = (time.perf_counter()-started)*1000
        size = service.db_path.stat().st_size/1024
        print(f'Pedidos creados: {args.orders:,}')
        print(f'Registro total: {elapsed:.3f} s')
        print(f'Registro promedio: {(elapsed/args.orders)*1000:.4f} ms/pedido')
        print(f'Preparar un pedido con {args.orders:,} en memoria: {process_ms:.4f} ms ({record["code"]})')
        print(f'Consultar contadores: {status_ms:.4f} ms | Pendientes: {status["orders_pending"]:,}')
        print(f'Tamaño base SQLite principal: {size:.1f} KiB (WAL temporal no incluido)')
        print('Resultados orientativos; dependen del disco, CPU, SO y condiciones de ejecución.')
        service._db.close()


if __name__ == '__main__':
    main()
