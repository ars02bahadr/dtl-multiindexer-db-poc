use sqlx::postgres::PgPoolOptions;
use sqlx::{Pool, Postgres, Row};
use std::env;
use dtl_domain::{User, Transaction};

pub type DbPool = Pool<Postgres>;

pub async fn init_pool() -> Result<DbPool, sqlx::Error> {
    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgres://user:password@localhost:5433/dtl_db".to_string());

    PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
}

pub async fn create_tables(pool: &DbPool) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            address VARCHAR(42) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            balance BIGINT DEFAULT 0
        )
        "#
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR(100) PRIMARY KEY,
            from_addr VARCHAR(42) NOT NULL,
            to_addr VARCHAR(42) NOT NULL,
            amount BIGINT NOT NULL,
            status VARCHAR(20) NOT NULL,
            ipfs_cid VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        )
        "#
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn seed_users(pool: &DbPool) -> Result<(), sqlx::Error> {
    // Clear existing data for clean demo
    sqlx::query("DELETE FROM users").execute(pool).await?;

    // Seed Alice and Bob with 1200 balance each
    sqlx::query(
        r#"
        INSERT INTO users (address, name, balance) VALUES
        ('0xfe3b557e8fb62b89f4916b721be55ceb828dbd73', 'Alice', 1200),
        ('0x627306090abab3a6e1400e9345bc60c78a8bef57', 'Bob', 1200)
        ON CONFLICT (address) DO UPDATE SET balance = EXCLUDED.balance
        "#
    )
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn get_all_users(pool: &DbPool) -> Result<Vec<User>, sqlx::Error> {
    let rows = sqlx::query("SELECT id, address, name, balance FROM users ORDER BY id")
        .fetch_all(pool)
        .await?;

    let users = rows.iter().map(|row| User {
        id: row.get("id"),
        address: row.get("address"),
        name: row.get("name"),
        balance: row.get::<i64, _>("balance") as u64,
    }).collect();

    Ok(users)
}

pub async fn transfer(pool: &DbPool, from_addr: &str, to_addr: &str, amount: u64) -> Result<(), sqlx::Error> {
    let mut tx = pool.begin().await?;

    // Deduct from sender
    sqlx::query("UPDATE users SET balance = balance - $1 WHERE address = $2")
        .bind(amount as i64)
        .bind(from_addr)
        .execute(&mut *tx)
        .await?;

    // Add to receiver
    sqlx::query("UPDATE users SET balance = balance + $1 WHERE address = $2")
        .bind(amount as i64)
        .bind(to_addr)
        .execute(&mut *tx)
        .await?;

    tx.commit().await?;
    Ok(())
}

pub async fn save_transaction(pool: &DbPool, tx: &Transaction) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        INSERT INTO transactions (id, from_addr, to_addr, amount, status, ipfs_cid)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
        "#
    )
    .bind(&tx.id)
    .bind(&tx.from)
    .bind(&tx.to)
    .bind(tx.amount as i64)
    .bind(&tx.status)
    .bind(&tx.ipfs_cid)
    .execute(pool)
    .await?;
    Ok(())
}

