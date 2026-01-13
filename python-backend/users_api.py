from flask import request
from flask_restx import Resource, Namespace, fields

api = Namespace('users', description='Kullanıcı işlemleri')

user_model = api.model('User', {
    'name': fields.String,
    'address': fields.String,
    'balance': fields.Integer
})

users_db = [
    {'name': 'Alice', 'address': '0xfe3b557e8fb62b89f4916b721be55ceb828dbd73', 'balance': 1200},
    {'name': 'Bob', 'address': '0x627306090abab3a6e1400e9345bc60c78a8bef57', 'balance': 1200}
]

@api.route('/')
class UserList(Resource):
    @api.doc('get_users')
    def get(self):
        """Tüm kullanıcıları listeler"""
        return users_db

@api.route('/seed')
class SeedUsers(Resource):
    @api.doc('seed_users')
    def post(self):
        """Demo kullanıcıları başlatır"""
        global users_db
        users_db = [
            {'name': 'Alice', 'address': '0xfe3b557e8fb62b89f4916b721be55ceb828dbd73', 'balance': 1200},
            {'name': 'Bob', 'address': '0x627306090abab3a6e1400e9345bc60c78a8bef57', 'balance': 1200}
        ]
        return {'status': 'seeded', 'users': users_db}
