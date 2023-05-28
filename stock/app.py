import os
import atexit

from flask import Flask, abort, jsonify
import redis
import json
import requests


app = Flask("stock-service")
gateway_url = os.environ['GATEWAY_URL']
db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()
atexit.register(close_db_connection)
@app.post('/item/create/<price>')
def create_item(price: int):
    item = {
        "item_id": db.incr("item_id"),
        "price": price,
        "stock": 0
    }

    db.set(item["item_id"], json.dumps(item))
    return {
        "CODE": 200,
        "item_id": item["item_id"],
    }

@app.get('/find/<item_id>')
def find_item(item_id: str):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")    
    # retrieve the item from the database
    item_found = json.loads(db.get(item_id))
    item_found["price"]= float(item_found["price"])
    item_found["stock"]= int(item_found["stock"])
    # return the item information using dictionary unpacking
    return {"CODE": 200, **item_found}
    


# @app.post('/add/<item_id>/<amount>')
# def add_stock(item_id: str, amount: int):
#     # check if the item exists
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")
#     item_found = json.loads(db.get(item_id))
#     item_found["stock"] = int(item_found["stock"])
#     item_found["stock"] += int(amount)
#     db.set(item_id, json.dumps(item_found))
#     # return {"CODE": 200}
#     # return {"status_code":200}
#     response = app.response_class(
#         response=item_found,
#         status=200,
#         mimetype='application/json'
#     )
#     return response

@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    # Check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")

    # Retrieve the item from the database
    item_found = json.loads(db.get(item_id))
    item_found["stock"] = int(item_found["stock"])
    
    # Call coordination service to start a new transaction
    response = requests.post(f"{gateway_url}/start_tx")
    if response.status_code == 200:
        conn_id = response.json()["conn_id"]
        
        # Update item stock in the transaction context
        item_found["stock"] += int(amount)
        db.set(item_id, json.dumps(item_found))
        
        # Prepare the transaction in the coordination service
        response = requests.post(f"{gateway_url}/prepare/{conn_id}")
        if response.status_code == 200:
            # Store the updated item stock value
            db.set(item_id, json.dumps(item_found))

            # Commit the transaction
            response = requests.post(f"{gateway_url}/commit_tx/{conn_id}")
            if response.status_code == 200:
                return {"message": "Stock added successfully"}
            else:
                # Handle commit failure
                return {"error": "Failed to commit transaction"}, 500
        else:
            # Handle prepare failure
            return {"error": "Failed to prepare transaction"}, 500
    else:
        # Handle transaction start failure
        return {"error": "Failed to start transaction"}, 500


@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")
    # Start the transaction
    response = requests.post(f"{gateway_url}/start_tx")
    if response.status_code == 200:
        conn_id = response.json()["conn_id"]
        # Get the current item stock value
        item_found = json.loads(db.get(item_id))
        item_found["stock"] = int(item_found["stock"])
        if item_found["stock"] < int(amount):
            abort(404, description=f"Not enough stock for item with id {item_id}")
        else:
            # Decrement the stock by the specified amount
            item_found["stock"] -= int(amount)

            # Prepare the transaction in the coordination service
            response = requests.post(f"{gateway_url}/prepare/{conn_id}")
            if response.status_code == 200:
                # Store the updated item stock value
                db.set(item_id, json.dumps(item_found))
                # Commit the transaction
                response = requests.post(f"{gateway_url}/commit_tx/{conn_id}")
                if response.status_code == 200:
                    return {"message": "Stock removed successfully"}
                else:
                    # Handle commit failure
                    return {"error": "Failed to commit transaction"}, 500
            else:
                # Handle prepare failure
                return {"error": "Failed to prepare transaction"}, 500
    else:
        # Handle transaction start failure
        return {"error": "Failed to start transaction"}, 500



        
# @app.post('/subtract/<item_id>/<amount>')
# def remove_stock(item_id: str, amount: int):
#     # check if the item exists
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")
#     item_found = json.loads(db.get(item_id))
#     item_found["stock"] = int(item_found["stock"])
#     if item_found["stock"] < int(amount):
#         abort(404, description=f"Not enough stock for item with id {item_id}")
#     else:
#         item_found["stock"] -= int(amount)
#         db.set(item_id, json.dumps(item_found))
#         response = app.response_class(
#         response="",
#         status=200,
#         mimetype='application/json'
#     )
#     return response
