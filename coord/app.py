import os
import atexit
import json
import requests
from collections import Counter
import uuid

from flask import Flask, abort, jsonify
import redis


app = Flask("coord-service")


db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))

def close_db_connection():
    db.close()
atexit.register(close_db_connection)

@app.post('/start_tx')
def start_transaction():
    # conn_id = str(db.incr("transaction_id"))
    conn_id = str(uuid.uuid4())
    db.set(conn_id, "STARTED")
    return jsonify({'conn_id': conn_id}), 200


@app.post('/exec/<conn_id>')
# @app.route('/exec/<conn_id>', methods=['POST'])
def execute_command(conn_id):
    if db.exists(conn_id):
        command = requests.json.get('command')
        db.rpush(f"{conn_id}:commands", command)
        return jsonify({'message': 'Command executed successfully'})
    else:
        return jsonify({'error': 'Invalid connection ID'}), 400

# @app.route('/commit_tx/<conn_id>', methods=['POST'])
@app.post('/commit_tx/<conn_id>')
def commit_transaction(conn_id):
    if db.exists(conn_id):
        db.rpush(f"{conn_id}:commands", "COMMIT")
        db.delete(conn_id)
        return jsonify({'message': 'Transaction committed successfully'})
    else:
        return jsonify({'error': 'Invalid connection ID'}), 400
@app.post('/cancel_tx/<conn_id>')
# @app.route('/cancel_tx/<conn_id>', methods=['POST'])
def cancel_transaction(conn_id):
    if db.exists(conn_id):
        db.rpush(f"{conn_id}:commands", "ROLLBACK")
        db.delete(conn_id)
        return jsonify({'message': 'Transaction cancelled successfully'})
    else:
        return jsonify({'error': 'Invalid connection ID'}), 400

# @app.route('/find/<item_id>', methods=['GET'])
# def find_item(item_id):
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")

#     item_found = db.get(item_id).decode('utf-8')
#     item_found = json.loads(item_found)
#     item_found["price"] = float(item_found["price"])
#     item_found["stock"] = int(item_found["stock"])

#     return jsonify({'CODE': 200, **item_found})