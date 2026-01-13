from flask import Flask
from flask_restx import Api

app = Flask(__name__)
api = Api(app, version='1.0', title='DTL Multiindexer API',
          description='Go ve Rust kodlarının Flask ile yeniden yazılmış hali',
          doc='/swagger/')


# API modüllerini ekle
from scheduler_api import api as scheduler_ns
from users_api import api as users_ns
from transfer_api import api as transfer_ns

from ipfs_api import api as ipfs_ns
from besu_api import api as besu_ns

api.add_namespace(scheduler_ns, path='/scheduler')
api.add_namespace(users_ns, path='/users')
api.add_namespace(transfer_ns, path='/transfer')

api.add_namespace(ipfs_ns, path='/ipfs')
api.add_namespace(besu_ns, path='/besu')

if __name__ == '__main__':
    app.run(debug=True)
