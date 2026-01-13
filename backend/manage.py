#!/usr/bin/env python3
"""
Flask CLI komutları ve yönetim scriptleri.
"""
import os
import sys
import click

# Module path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.app import create_app
from backend.extensions import db
from backend.models import User, Balance


app = create_app()


@app.cli.command('init-db')
def init_db():
    """Database tablolarını oluştur."""
    db.create_all()
    click.echo('Database tabloları oluşturuldu.')


@app.cli.command('drop-db')
@click.confirmation_option(prompt='TÜM VERİLER SİLİNECEK! Emin misiniz?')
def drop_db():
    """Database tablolarını sil."""
    db.drop_all()
    click.echo('Database tabloları silindi.')


@app.cli.command('create-admin')
@click.option('--username', prompt='Admin username', help='Admin kullanıcı adı')
@click.option('--password', prompt='Admin password', hide_input=True, confirmation_prompt=True)
@click.option('--address', prompt='Wallet address', help='Ethereum cüzdan adresi')
def create_admin(username, password, address):
    """Admin kullanıcı oluştur."""
    from werkzeug.security import generate_password_hash

    # Validasyon
    if User.query.filter_by(username=username).first():
        click.echo(f'HATA: "{username}" kullanıcısı zaten mevcut!', err=True)
        return

    if not address.startswith('0x') or len(address) != 42:
        click.echo('HATA: Geçerli bir Ethereum adresi girin (0x...)', err=True)
        return

    # Kullanıcı oluştur
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        address=address.lower(),
        role='admin'
    )
    db.session.add(user)

    # Başlangıç bakiyesi
    balance = Balance(user=user, amount=0)
    db.session.add(balance)

    db.session.commit()

    click.echo(f'Admin kullanıcı oluşturuldu: {username} (ID: {user.id})')


@app.cli.command('list-users')
def list_users():
    """Tüm kullanıcıları listele."""
    users = User.query.all()

    if not users:
        click.echo('Henüz kullanıcı yok.')
        return

    click.echo(f'{"ID":<5} {"Username":<20} {"Role":<10} {"Address":<44}')
    click.echo('-' * 80)

    for user in users:
        click.echo(f'{user.id:<5} {user.username:<20} {user.role:<10} {user.address}')


@app.cli.command('seed-demo')
def seed_demo():
    """Demo verileri oluştur."""
    from werkzeug.security import generate_password_hash
    from decimal import Decimal

    # Demo kullanıcılar
    demo_users = [
        ('alice', 'password123', '0x1111111111111111111111111111111111111111', 'user'),
        ('bob', 'password123', '0x2222222222222222222222222222222222222222', 'user'),
        ('admin', 'admin123', '0x0000000000000000000000000000000000000001', 'admin'),
    ]

    for username, password, address, role in demo_users:
        if User.query.filter_by(username=username).first():
            click.echo(f'Atlandı: {username} (zaten mevcut)')
            continue

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            address=address.lower(),
            role=role
        )
        db.session.add(user)
        db.session.flush()

        # Başlangıç bakiyesi
        initial_balance = Decimal('1000') if role == 'admin' else Decimal('100')
        balance = Balance(user_id=user.id, amount=initial_balance)
        db.session.add(balance)

        click.echo(f'Oluşturuldu: {username} (rol: {role}, bakiye: {initial_balance})')

    db.session.commit()
    click.echo('Demo verileri oluşturuldu!')


if __name__ == '__main__':
    app.run()
