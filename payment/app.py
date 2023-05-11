import os
import atexit

from flask import Flask, abort
import redis
import json


app = Flask("payment-service")

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/create_user')
def create_user():
    user= {
        "user_id": db.incr("user_id"),
        "credit": 0,
    }

    db.set(user["user_id"], json.dumps(user))

    response = app.response_class(
        response=json.dumps(user),
        status=200,
        mimetype='application/json'
    )
    return response


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    # check if the user exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")

    # retrieve the user from the database
    user_found = json.loads(db.get(user_id))
    
    # return the user information using dictionary unpacking
    response = app.response_class(
        response=json.dumps(user_found),
        status=200,
        mimetype='application/json'
    )
    return response
    # return {"CODE": 200, **user_found}


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    # Check if user exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")
    
    # retrieve the user from the database
    user_found = json.loads(db.get(user_id))

    # Update the user amount in the dict
    user_found["credit"] = float(user_found["credit"]) + float(amount)

    # Update the database
    db.set(user_found["user_id"], json.dumps(user_found))

    # return the user information using dictionary unpacking
    response = app.response_class(
        response=json.dumps(user_found),
        status=200,
        mimetype='application/json'
    )
    return response
    # return {"status_code": 200, **user_found}


### Do i need to check that this order id belongs to the user id?
### Why can i select an amount here? shouldnt the amount be equal to the order's total cost??
### Unless u can pay partially? which make senses

### Definitely wrong
@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    # Check if user and order exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")
    
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")

    # retrieve the user from the database
    user_found = json.loads(db.get(user_id))

    # Check if user has sufficient amount to deduct
    if float(user_found['credit']) < float(amount):
        abort(400, description=f"User with id {user_id} does not have sufficient amount to be deducted")

    # Update the user amount in the dict
    user_found["credit"] = float(user_found["credit"]) - float(amount)

    # Update the database
    db.set(user_found["user_id"], json.dumps(user_found))

    # retrieve the order from the database
    order_found = json.loads(db.get(order_id))
    
    # Amount > total cost -> Fail
    if float(amount) > (float(order_found["total_cost"])- float(order_found["paid_amount"])):
        abort(400, description=f"{amount} paid is more than required")

    # add paid amount
    order_found["paid_amount"] = float(order_found["paid_amount"]) + float(amount)

    if order_found["paid_amount"] == order_found["total_cost"]:
        order_found["payment_status"] = "Completed"

    db.set(order_found["order_id"], json.dumps(order_found))

    data = user_found.update(order_found)

    # return the user information using dictionary unpacking
    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response
    # return {"CODE": 200, **user_found, **order_found}


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    # Check if user and order exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")
    
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    pass

@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    pass
