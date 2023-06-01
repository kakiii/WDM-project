import unittest

import utils as tu

class newtest(unittest.TestCase):

    def test_add_negative_price_item(self):
        #create an item  with negative price and check if it is not added
        item: dict = tu.create_item(-1)
        self.assertFalse("item_id" in item)
    
    def test_add_zero_price_item(self):
        #create an item with zero price and check if it is not added
        item: dict = tu.create_item(0)
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


if __name__ == '__main__':
    unittest.main()
        
    

