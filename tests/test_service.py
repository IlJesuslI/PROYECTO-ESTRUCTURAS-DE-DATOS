"""Pruebas funcionales, integridad, migración y complejidad de FoodQueue v3."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.service import ConflictError, FoodQueueService, NotFoundError, ValidationError


class FoodQueueServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.json'
        self.service = FoodQueueService(self.path)
        self.product = self.service.list_products()[0]

    def tearDown(self):
        self.service._db.close()
        self.tmp.cleanup()

    def make_order(self, customer='Cliente', priority=0, quantity=1):
        return self.service.create_order({
            'customer': customer, 'priority': priority,
            'items': [{'product_id': self.product['id'], 'quantity': quantity}]
        })

    def test_fifo_normal(self):
        a = self.make_order('A'); b = self.make_order('B')
        self.assertEqual(self.service.process_next_order()['id'], a['id'])
        self.assertEqual(self.service.process_next_order()['id'], b['id'])

    def test_high_before_normal(self):
        normal = self.make_order('Normal')
        high = self.make_order('Alta', 1)
        self.assertEqual(self.service.process_next_order()['id'], high['id'])
        self.assertEqual(self.service.process_next_order()['id'], normal['id'])

    def test_fifo_within_high(self):
        a = self.make_order('Alta1', 1)
        b = self.make_order('Alta2', 1)
        self.assertEqual(self.service.process_next_order()['id'], a['id'])
        self.assertEqual(self.service.process_next_order()['id'], b['id'])

    def test_reject_priority_2(self):
        with self.assertRaises(ValidationError):
            self.make_order('Urgente', 2)

    def test_fairness_three_high_then_normal(self):
        normal = self.make_order('N', 0)
        highs = [self.make_order(str(i), 1) for i in range(4)]
        result = [self.service.process_next_order()['id'] for _ in range(5)]
        self.assertEqual(result, [highs[0]['id'], highs[1]['id'], highs[2]['id'], normal['id'], highs[3]['id']])

    def test_no_starvation_after_many_high(self):
        normal = [self.make_order(f'n{i}') for i in range(30)]
        highs = [self.make_order(f'h{i}', 1) for i in range(100)]
        result = [self.service.process_next_order()['id'] for _ in range(40)]
        self.assertEqual(result[3::4], [p['id'] for p in normal[:10]])

    def test_cancel_does_not_scan_or_block_queue(self):
        a = self.make_order('A'); b = self.make_order('B'); c = self.make_order('C')
        self.service.cancel_order(b['id'])
        self.assertEqual(self.service.process_next_order()['id'], a['id'])
        self.assertEqual(self.service.process_next_order()['id'], c['id'])
        self.assertEqual(self.service.status()['normal_queue_size'], 0)
        with self.assertRaises(NotFoundError):
            self.service.process_next_order()

    def test_cancel_high_from_front(self):
        a = self.make_order('A', 1); b = self.make_order('B', 1)
        self.service.cancel_order(a['id'])
        self.assertEqual(self.service.process_next_order()['id'], b['id'])

    def test_status_matches_after_mutations(self):
        a = self.make_order('A'); b = self.make_order('B', 1)
        self.service.cancel_order(a['id'])
        self.service.process_next_order()
        self.assertEqual(self.service.status()['orders_pending'], 0)
        self.assertEqual(self.service.status()['orders_prepared'], 1)
        self.assertEqual(self.service.status()['orders_cancelled'], 1)

    def test_stack_remains_lifo_in_history(self):
        a = self.make_order('A'); b = self.make_order('B')
        self.service.process_next_order(); self.service.process_next_order()
        self.assertEqual([o['id'] for o in self.service.list_history()], [b['id'], a['id']])

    def test_delete_single_prepared(self):
        a = self.make_order('A'); b = self.make_order('B')
        self.service.process_next_order(); self.service.process_next_order()
        deleted = self.service.delete_history_order(a['id'])
        self.assertEqual(deleted['id'], a['id'])
        self.assertEqual([o['id'] for o in self.service.list_history()], [b['id']])
        self.assertEqual(self.service.status()['orders_prepared'], 1)
        with self.assertRaises(NotFoundError):
            self.service.delete_history_order(a['id'])

    def test_cannot_delete_pending_from_history(self):
        a = self.make_order('A')
        with self.assertRaises(ConflictError):
            self.service.delete_history_order(a['id'])

    def test_clear_only_prepared(self):
        a = self.make_order('A'); b = self.make_order('B')
        self.service.process_next_order()
        self.assertEqual(self.service.clear_history(), 1)
        self.assertEqual(self.service.list_history(), [])
        self.assertEqual(self.service.status()['orders_pending'], 1)
        self.assertEqual(self.service.process_next_order()['id'], b['id'])

    def test_restart_preserves_queue_order(self):
        n1 = self.make_order('N1'); n2 = self.make_order('N2')
        h1 = self.make_order('H1', 1); h2 = self.make_order('H2', 1)
        another = FoodQueueService(self.path)
        try:
            self.assertEqual([another.process_next_order()['id'] for _ in range(4)],
                             [h1['id'], h2['id'], n1['id'], n2['id']])
        finally:
            another._db.close()

    def test_restart_preserves_deletion(self):
        a = self.make_order('A'); self.service.process_next_order()
        self.service.delete_history_order(a['id'])
        another = FoodQueueService(self.path)
        try:
            self.assertEqual(another.list_history(), [])
            self.assertEqual(another.status()['orders_prepared'], 0)
        finally:
            another._db.close()

    def test_history_pagination(self):
        for i in range(12):
            self.make_order(str(i)); self.service.process_next_order()
        one = self.service.list_history(limit=5, offset=0)
        two = self.service.list_history(limit=5, offset=5)
        self.assertEqual(len(one), 5)
        self.assertEqual(len(two), 5)
        self.assertTrue(set(o['id'] for o in one).isdisjoint(o['id'] for o in two))

    def test_inactive_product_cannot_order(self):
        self.service.deactivate_product(self.product['id'])
        with self.assertRaises(ValidationError):
            self.make_order()

    def test_duplicate_products(self):
        with self.assertRaises(ConflictError):
            self.service.add_product({'name': self.product['name'], 'price_cop': 5000})

    def test_bad_quantities(self):
        for value in [100, 0, -1, 2.7, True, '3.9']:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.make_order(quantity=value)

    def test_no_undo_method(self):
        self.assertFalse(hasattr(self.service, 'undo_last_prepared'))

    def test_thousands_of_cancelled_items_still_work(self):
        ids = [self.make_order(str(i), 1) for i in range(1100)]
        for order in ids[:-1]:
            self.service.cancel_order(order['id'])
        self.assertEqual(self.service.process_next_order()['id'], ids[-1]['id'])
        self.assertEqual(self.service.status()['priority_queue_size'], 0)

    def test_pending_shows_real_interleaved_order(self):
        normal = self.make_order('Normal')
        highs = [self.make_order(f'High {i}', 1) for i in range(4)]
        self.assertEqual([o['id'] for o in self.service.list_pending_orders(5)],
                         [highs[0]['id'], highs[1]['id'], highs[2]['id'], normal['id'], highs[3]['id']])


class MigrationTests(unittest.TestCase):
    def test_sqlite_priority_2_is_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            service = FoodQueueService(path)
            pid = service.list_products()[0]['id']
            data = service.create_order({'customer':'Old','priority':1,
                                         'items':[{'product_id':pid,'quantity':1}]})
            with service._db:
                raw = json.loads(service._db.execute('SELECT payload FROM orders WHERE id=?', (data['id'],)).fetchone()[0])
                raw['priority'] = 2
                service._db.execute('UPDATE orders SET priority=2,payload=? WHERE id=?',
                                    (json.dumps(raw),data['id']))
                service._db.execute('UPDATE metadata SET value=2 WHERE key=?',('schema_version',))
            service._db.close()
            new = FoodQueueService(path)
            try:
                self.assertEqual(new.process_next_order()['priority'], 1)
                self.assertEqual(new._db.execute('SELECT priority FROM orders WHERE id=?',
                                 (data['id'],)).fetchone()[0], 1)
            finally:
                new._db.close()

    def test_json_priority_heap_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            seed = FoodQueueService(path)
            product = seed.list_products()[0]
            orders = [seed.create_order({'customer':str(i), 'priority':1,
                'items':[{'product_id':product['id'],'quantity':1}]}) for i in range(3)]
            legacy = {'version':2,'next_order_number':4,'products':seed.list_products(True),
                'orders':[{**o, 'priority':2 if i==1 else 1} for i,o in enumerate(orders)],
                'normal_queue':[],
                'priority_queue':[[-2,2,orders[1]['id']],[-1,1,orders[0]['id']],[-1,3,orders[2]['id']]],
                'prepared_stack':[]}
            seed._db.close(); path.with_suffix('.sqlite3').unlink()
            path.write_text(json.dumps(legacy), encoding='utf-8')
            new = FoodQueueService(path)
            try:
                self.assertEqual([new.process_next_order()['id'] for _ in range(3)],
                                 [o['id'] for o in orders])
            finally:
                new._db.close()


if __name__ == '__main__':
    unittest.main()
