import os
import atexit
import json
import requests
from uuid import uuid4
from collections import Counter

from flask import Flask, abort, jsonify
import redis
import uuid

# gateway_url = os.environ['GATEWAY_URL']

stock_service = os.environ['STOCK_SERVICE_URL']
payment_service = os.environ['USER_SERVICE_URL']
coord_service = os.environ['COORD_SERVICE_URL']


app = Flask("order-service")

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/create/<user_id>')
def create_order(user_id:str):
    order= {
        "order_id": str(uuid.uuid4()),
        "user_id": user_id,
        "items": [],
        "paid": False,
        "total_cost": 0,
    }
    db.set(order["order_id"], json.dumps(order))

    return jsonify(order), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id:str):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    # delete the order from the database
    db.delete(order_id)
    
    response = app.response_class(
            response= f"{order_id} order has been deleted",
            status=200,
            mimetype='application/json'
        )
    return f"{order_id} order has been deleted", 200



@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id:str, item_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")

    order_found = json.loads(db.get(order_id))
    order_found["items"].append(item_id)

    # update total cost
    response = requests.get(f"{stock_service}/stock/find/{item_id}")
    item_price = response.json()["price"]
    order_found["total_cost"] += item_price
    db.set(order_id, json.dumps(order_found))

    return jsonify(order_found), 200



@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    order_found = json.loads(db.get(order_id))
    if item_id not in order_found["items"]:
        abort(404, description=f"Item with id {item_id} not found in order with id {order_id}")
    else:
        order_found["items"].remove(item_id)
        # update total cost
        item_price = int(requests.get(f"{stock_service}/stock/find/{item_id}").json()["price"])
        order_found["total_cost"] -= item_price
        db.set(order_id, json.dumps(order_found))

        return jsonify(order_found), 200

@app.get('/find/<order_id>')
def find_order(order_id:str):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    # retrieve the order from the database
    order_found = json.loads(db.get(order_id))
    
    return jsonify(order_found), 200

@app.post('/checkout/<order_id>')
def checkout(order_id):
    # Retrieve the order from the database
    order_found = json.loads(db.get(order_id))

    if order_found["paid"]:
        abort(400, description="Order has already been paid")

    checkout_lock = db.lock("checkout_lock", timeout=10)
    if checkout_lock.acquire():
        try:
            # Transform list of items into a dictionary
            items_count = Counter(order_found["items"])

            # Call the coordinator service to start a new transaction
            response = requests.post(f"{coord_service}/start_tx")
            if response.status_code != 200:
                abort(response.status_code, description="Failed to start the transaction")

            transaction_data = response.json()
            conn_id = transaction_data['conn_id']

            # Update the stock information and order information
            for item_id, count in items_count.items():
                response = requests.post(f"{stock_service}subtract/{item_id}/{count}")
                if response.status_code != 200:
                    res = requests.post(f"{coord_service}/cancel_tx/{conn_id}")
                    return res.content, response.status_code

                requests.post(f"{coord_service}/coord/addItem/{conn_id}/{item_id}/{count}")
                        
            # Query the payment service to process the payment
            response = requests.post(f"{payment_service}/pay/{order_found['user_id']}/{order_id}/{int(order_found['total_cost'])}")
            if response.status_code != 200:
                requests.post(f"{coord_service}/cancel_tx/{conn_id}")
                return "Cash not available in checkout", response.status_code
            else:
                requests.post(f"{coord_service}/addPayment/{conn_id}/{order_found['user_id']}/{int(order_found['total_cost'])}")
                

            # Call the coordinator service to commit the transaction
            response = requests.post(f"{coord_service}/commit_tx/{conn_id}")
            if response.status_code != 200:
                res = requests.get(f"{coord_service}/find/{conn_id}")
                return "Failed to commit the transaction", response.status_code
            
            # Mark the order as paid
            order_found["paid"] = True
            db.set(order_id, json.dumps(order_found))
            return jsonify(order_found), 200
        except Exception as e:
            return "Exception occured", 400
        finally:
            checkout_lock.release()


