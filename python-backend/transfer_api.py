from flask import request
from flask_restx import Resource, Namespace, fields

api = Namespace('transfer', description='Transfer işlemleri')

transfer_model = api.model('Transfer', {
    'from': fields.String(required=True),
    'to': fields.String(required=True),
    'amount': fields.Integer(required=True)
})

users_db = [
    {'name': 'Alice', 'address': '0xfe3b557e8fb62b89f4916b721be55ceb828dbd73', 'balance': 1200},
    {'name': 'Bob', 'address': '0x627306090abab3a6e1400e9345bc60c78a8bef57', 'balance': 1200}
]

@api.route('/')
class Transfer(Resource):
    @api.doc('transfer')
    @api.expect(transfer_model)
    def post(self):
        """Kullanıcılar arasında transfer yapar"""
        data = request.json
        sender = next((u for u in users_db if u['address'] == data['from']), None)
        receiver = next((u for u in users_db if u['address'] == data['to']), None)
        amount = data['amount']
        if not sender or not receiver:
            return {'error': 'Kullanıcı bulunamadı'}, 404
        if sender['balance'] < amount:
            return {'error': 'Bakiye yetersiz'}, 400
        sender['balance'] -= amount
        receiver['balance'] += amount
        return {'status': 'success', 'from': sender['address'], 'to': receiver['address'], 'amount': amount}
