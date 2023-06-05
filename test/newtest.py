import unittest
import threading
import utils as tu

class newtest(unittest.TestCase):


    def test_concurrent_add_stock(self):
        # Create an item
        item = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id = item['item_id']

        # Define a function to add stock
        def add_stock():
            tu.add_stock(item_id, 1)

        # Start multiple threads that add stock at the same time
        threads = [threading.Thread(target=add_stock) for _ in range(10000)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of stock was added
        item = tu.find_item(item_id)
        self.assertEqual(item['stock'], 10000)

    def test_concurrent_subtract_stock(self):
        # Create an item and add some stock
        item = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id = item['item_id']
        tu.add_stock(item_id, 10)

        # Define a function to subtract stock
        def subtract_stock():
            tu.subtract_stock(item_id, 1)

        # Start multiple threads that subtract stock at the same time
        threads = [threading.Thread(target=subtract_stock) for _ in range(10000)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of stock was subtracted
        item = tu.find_item(item_id)
        self.assertEqual(item['stock'], 0)

    def test_concurrent_add_credit(self):
        # Create a user
        user = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id = user['user_id']

        # Define a function to add credit
        def add_credit():
            tu.add_credit_to_user(user_id, 1)

        # Start multiple threads that add credit at the same time
        threads = [threading.Thread(target=add_credit) for _ in range(10000)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of credit was added
        user = tu.find_user(user_id)
        self.assertEqual(user['credit'], 10000)

    def test_concurrent_checkout(self):
        user = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id = user['user_id']
        tu.add_credit_to_user(user['user_id'], 10000)
        item = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id = item['item_id']
        tu.add_stock(item_id, 10000)
        
        order_ids = []
        for _ in range(10000):
            order = tu.create_order(user_id)
            tu.add_item_to_order(order['order_id'], item_id)
            order_ids.append(order['order_id'])

        
        #checkout all orders in the order_ids   
        def checkout_order():
            tu.checkout_order(order_ids[0])
            order_ids.pop(0)
            tu.subtract_stock(item_id, 1)


        threads_checkout = [threading.Thread(target=checkout_order) for _ in range(10000)]
        for thread in threads_checkout:
            thread.start()
            thread.join()
        
        #check if there is no stock left
        item = tu.find_item(item_id)
        self.assertEqual(item['stock'], 0)
        #check if credit is reduced
        


        

if __name__ == '__main__':
    unittest.main()
        
    

