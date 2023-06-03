import unittest
import threading
import utils as tu

class newtest(unittest.TestCase):

    def test_add_negative_price_item(self):
        #create an item  with negative price and check if it is not added
        item: dict = tu.create_item(-1)
        self.assertFalse("item_id" in item)
    

    def test_subtract_more_than_available(self):
        #check if subtracting more than available quantity works
        item: dict = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id: str = item['item_id']
        self.assertTrue(tu.status_code_is_failure(tu.subtract_stock(item_id, 2)))

    
    def test_add_negative_amount_item(self):
        #Check if adding negative amount of item works
        item: dict = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id: str = item['item_id']
        self.assertTrue(tu.status_code_is_failure(tu.add_stock(item_id, -1)))

    def test_checkout_without_order(self):
        #Check if checkout without order works
        self.assertTrue(tu.status_code_is_failure(tu.checkout_order('').status_code))


    def test_add_negative_credit_to_user(self):
        user: dict = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id: str = user['user_id']
        self.assertTrue(tu.status_code_is_failure(tu.add_credit_to_user(user_id, -1)))

    def test_add_zero_credit_to_user(self):
        user: dict = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id: str = user['user_id']
        self.assertTrue(tu.status_code_is_failure(tu.add_credit_to_user(user_id, 0)))

    def test_add_out_of_stock_item_to_order(self):
        #Check if adding out of stock item to order works
        item: dict = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id: str = item['item_id']
        order: dict = tu.create_order(item_id)
        self.assertFalse('order_id' in order)

########Multi-Threading Tests########

    def test_concurrent_add_stock(self):
        # Create an item
        item = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id = item['item_id']

        # Define a function to add stock
        def add_stock():
            tu.add_stock(item_id, 1)

        # Start multiple threads that add stock at the same time
        threads = [threading.Thread(target=add_stock) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of stock was added
        item = tu.find_item(item_id)
        self.assertEqual(item['stock'], 10)

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
        threads = [threading.Thread(target=subtract_stock) for _ in range(10)]
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
        threads = [threading.Thread(target=add_credit) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of credit was added
        user = tu.find_user(user_id)
        self.assertEqual(user['credit'], 10)

    def test_concurrent_remove_credit(self):
        # Create a user and add some credit
        user = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id = user['user_id']
        tu.add_credit_to_user(user_id, 10)

        # Define a function to remove credit
        def remove_credit():
            tu.remove_credit_from_user(user_id, 1)

        # Start multiple threads that remove credit at the same time
        threads = [threading.Thread(target=remove_credit) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of credit was removed
        user = tu.find_user(user_id)
        self.assertEqual(user['credit'], 0)

    def test_concurrent_checkout(self):
        # Create an item and add some stock
        item = tu.create_item(1)
        self.assertTrue('item_id' in item)
        item_id = item['item_id']
        tu.add_stock(item_id, 10)

        # Create a user and add some credit
        user = tu.create_user()
        self.assertTrue('user_id' in user)
        user_id = user['user_id']
        tu.add_credit_to_user(user_id, 10)

        # Define a function to checkout an order
        def checkout():
            tu.checkout_order(item_id)

        # Start multiple threads that checkout an order at the same time
        threads = [threading.Thread(target=checkout) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that the correct total amount of credit was added
        user = tu.find_user(user_id)
        self.assertEqual(user['credit'], 0)




if __name__ == '__main__':
    unittest.main()
        
    

