import tempfile
import unittest
from pathlib import Path

from app.service import ConflictError, FoodQueueService, ValidationError


class FoodQueueServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = FoodQueueService(Path(self.tmp.name) / "state.json")
        self.product = self.service.list_products()[0]

    def tearDown(self):
        self.tmp.cleanup()

    def make_order(self, customer="Cliente", priority=0, quantity=1):
        return self.service.create_order({
            "customer": customer,
            "priority": priority,
            "items": [{"product_id": self.product["id"], "quantity": quantity}],
        })

    def test_normal_queue_is_fifo(self):
        a = self.make_order("A")
        b = self.make_order("B")
        self.assertEqual(self.service.process_next_order()["id"], a["id"])
        self.assertEqual(self.service.process_next_order()["id"], b["id"])

    def test_priority_queue_orders_by_priority_then_arrival(self):
        normal = self.make_order("Normal", 0)
        high = self.make_order("Alta", 1)
        urgent = self.make_order("Urgente", 2)
        self.assertEqual(self.service.process_next_order()["id"], urgent["id"])
        self.assertEqual(self.service.process_next_order()["id"], high["id"])
        self.assertEqual(self.service.process_next_order()["id"], normal["id"])

    def test_fairness_after_three_priority_orders(self):
        normal = self.make_order("Normal", 0)
        priorities = [self.make_order(f"P{i}", 2) for i in range(4)]
        self.assertEqual(self.service.process_next_order()["id"], priorities[0]["id"])
        self.assertEqual(self.service.process_next_order()["id"], priorities[1]["id"])
        self.assertEqual(self.service.process_next_order()["id"], priorities[2]["id"])
        self.assertEqual(self.service.process_next_order()["id"], normal["id"])
        self.assertEqual(self.service.process_next_order()["id"], priorities[3]["id"])

    def test_stack_undo_is_lifo(self):
        a = self.make_order("A")
        b = self.make_order("B")
        self.service.process_next_order()
        self.service.process_next_order()
        undone = self.service.undo_last_prepared()
        self.assertEqual(undone["id"], b["id"])
        self.assertEqual(self.service.process_next_order()["id"], b["id"])
        self.assertNotEqual(a["id"], b["id"])

    def test_inactive_product_cannot_be_ordered(self):
        self.service.deactivate_product(self.product["id"])
        with self.assertRaises(ValidationError):
            self.make_order()

    def test_duplicate_active_product_name_is_rejected(self):
        with self.assertRaises(ConflictError):
            self.service.add_product({"name": self.product["name"], "price_cop": 10000})

    def test_quantity_limit_is_enforced(self):
        with self.assertRaises(ValidationError):
            self.make_order(quantity=100)

    def test_persistence_rebuilds_structures(self):
        order = self.make_order("Persistente", 2)
        reloaded = FoodQueueService(Path(self.tmp.name) / "state.json")
        self.assertEqual(reloaded.process_next_order()["id"], order["id"])

    def test_restart_preserves_requeued_position(self):
        first = self.make_order("Primero", 0)
        second = self.make_order("Segundo", 0)
        self.service.process_next_order()
        self.service.undo_last_prepared()  # Primero vuelve al final: Segundo -> Primero
        reloaded = FoodQueueService(Path(self.tmp.name) / "state.json")
        self.assertEqual(reloaded.process_next_order()["id"], second["id"])
        self.assertEqual(reloaded.process_next_order()["id"], first["id"])

    def test_restart_preserves_stack_order(self):
        normal = self.make_order("Normal", 0)
        urgent = self.make_order("Urgente", 2)
        prepared_urgent = self.service.process_next_order()
        prepared_normal = self.service.process_next_order()
        self.assertEqual(prepared_urgent["id"], urgent["id"])
        self.assertEqual(prepared_normal["id"], normal["id"])
        reloaded = FoodQueueService(Path(self.tmp.name) / "state.json")
        self.assertEqual(reloaded.undo_last_prepared()["id"], normal["id"])


if __name__ == "__main__":
    unittest.main()
