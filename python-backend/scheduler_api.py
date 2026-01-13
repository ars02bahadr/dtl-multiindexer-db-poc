from flask import request
from flask_restx import Resource, Namespace, fields
import requests
import time
import os

api = Namespace('scheduler', description='Scheduler işlemleri')

scheduler_model = api.model('Scheduler', {
    'besu_url': fields.String(required=True),
    'interval': fields.Integer(required=True),
    'besu_log_file': fields.String(required=True)
})

@api.route('/run_job')
class RunJob(Resource):
    @api.doc('run_job')
    @api.expect(scheduler_model)
    def post(self):
        """Scheduler jobunu çalıştırır ve log dosyasına yazar"""
        data = request.json
        besu_url = data['besu_url']
        interval = data['interval']
        besu_log_file = data['besu_log_file']
        # Örnek: blok numarası çekme
        try:
            response = requests.post(besu_url, json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }, timeout=10)
            block_number = response.json().get('result')
            with open(besu_log_file, 'a') as f:
                f.write(f"Block Number: {block_number}\n")
            return {'status': 'ok', 'block_number': block_number}
        except Exception as e:
            return {'error': str(e)}, 500
