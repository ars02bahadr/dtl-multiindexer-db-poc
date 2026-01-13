from flask import request
from flask_restx import Resource, Namespace, fields
import requests

api = Namespace('ipfs', description='IPFS işlemleri')

ipfs_model = api.model('IPFSAdd', {
    'data': fields.String(required=True)
})

IPFS_API_URL = 'http://127.0.0.1:5001/api/v0'

@api.route('/add')
class IPFSAdd(Resource):
    @api.doc('add_ipfs')
    @api.expect(ipfs_model)
    def post(self):
        """IPFS'ye veri ekler"""
        data = request.json['data']
        files = {'file': data.encode()}
        try:
            response = requests.post(f'{IPFS_API_URL}/add', files=files)
            result = response.json()
            return {'cid': result.get('Hash')}
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/cat/<string:cid>')
class IPFSCat(Resource):
    @api.doc('cat_ipfs')
    def get(self, cid):
        """IPFS'den veri okur"""
        try:
            response = requests.post(f'{IPFS_API_URL}/cat?arg={cid}')
            return {'data': response.text}
        except Exception as e:
            return {'error': str(e)}, 500
