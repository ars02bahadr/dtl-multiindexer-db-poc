from flask import request
from flask_restx import Resource, Namespace, fields
import requests

api = Namespace('besu', description='Besu işlemleri')

besu_model = api.model('BesuRPC', {
    'method': fields.String(required=True),
    'params': fields.List(fields.Raw, required=False)
})

BESU_URL = 'http://127.0.0.1:8545'

@api.route('/rpc')
class BesuRPC(Resource):
    @api.doc('besu_rpc')
    @api.expect(besu_model)
    def post(self):
        """Besu JSON-RPC çağrısı yapar"""
        data = request.json
        method = data['method']
        params = data.get('params', [])
        try:
            response = requests.post(BESU_URL, json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            })
            return response.json()
        except Exception as e:
            return {'error': str(e)}, 500
