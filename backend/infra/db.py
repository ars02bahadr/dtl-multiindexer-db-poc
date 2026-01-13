"""
Database yardımcı fonksiyonları ve utilities.
"""
from backend.extensions import db


def init_database(app):
    """
    Database'i başlat ve tabloları oluştur.
    Development için kullanışlı.
    """
    with app.app_context():
        db.create_all()


def drop_database(app):
    """
    Tüm tabloları sil.
    DİKKAT: Tüm veri silinir!
    """
    with app.app_context():
        db.drop_all()


def reset_database(app):
    """
    Database'i sıfırla (drop + create).
    DİKKAT: Tüm veri silinir!
    """
    drop_database(app)
    init_database(app)
