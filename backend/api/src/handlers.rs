use actix_web::{web, HttpResponse, Responder};
use serde::{Deserialize, Serialize};
use dtl_infra::db::DbPool;
use dtl_domain::{User, Transaction};
use uuid::Uuid;
use serde_json::json;

#[derive(Deserialize)]
pub struct TransferRequest {
    pub from: String,
    pub to: String,
    pub amount: u64,
}

// Hardcoded keys for PoC (Genesis accounts)
fn get_private_key(address: &str) -> Option<&'static str> {
    match address.to_lowercase().as_str() {
        "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73" => Some("8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c691be68"),
        "0x627306090abab3a6e1400e9345bc60c78a8bef57" => Some("c87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3"),
        _ => None,
    }
}

#[derive(Serialize)]
pub struct TransferResponse {
    pub status: String,
    pub tx_id: String,
    pub ipfs_cid: Option<String>,
}

// GET /users - List all users with balances
pub async fn get_users(pool: web::Data<DbPool>) -> impl Responder {
    match dtl_infra::db::get_all_users(pool.get_ref()).await {
        Ok(users) => HttpResponse::Ok().json(users),
        Err(e) => HttpResponse::InternalServerError().json(json!({"error": e.to_string()})),
    }
}

// POST /seed - Initialize demo users
pub async fn seed_users(pool: web::Data<DbPool>) -> impl Responder {
    // Create tables first
    if let Err(e) = dtl_infra::db::create_tables(pool.get_ref()).await {
        return HttpResponse::InternalServerError().json(json!({"error": e.to_string()}));
    }

    // Seed users
    match dtl_infra::db::seed_users(pool.get_ref()).await {
        Ok(_) => HttpResponse::Ok().json(json!({
            "status": "seeded",
            "users": [
                {"name": "Alice", "address": "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73", "balance": 1200},
                {"name": "Bob", "address": "0x627306090abab3a6e1400e9345bc60c78a8bef57", "balance": 1200}
            ]
        })),
        Err(e) => HttpResponse::InternalServerError().json(json!({"error": e.to_string()})),
    }
}

// POST /transfer - Transfer between users
pub async fn transfer(
    req: web::Json<TransferRequest>,
    pool: web::Data<DbPool>,
) -> impl Responder {
    let pk = match get_private_key(&req.from) {
        Some(k) => k,
        None => return HttpResponse::BadRequest().json(json!({"error": "Unknown sender address"})),
    };

    // 1. Initialize Contract
    let contract_addr = "0xa5A19a794fc1ec3010F832Dee431cF81D55D7Aee";
    let contract = match dtl_infra::contract::MoneyTokenContract::new(
        contract_addr,
        "http://localhost:8545" // Besu RPC
    ) {
        Ok(c) => c,
        Err(e) => return HttpResponse::InternalServerError().json(json!({"error": format!("Contract init failed: {}", e)})),
    };

    // 2. Upload metadata to IPFS
    let metadata = json!({
        "from": req.from,
        "to": req.to,
        "amount": req.amount,
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "type": "MoneyToken Transfer"
    });

    let ipfs_cid = match dtl_infra::ipfs::upload_json(&metadata).await {
        Ok(cid) => Some(cid),
        Err(e) => {
            println!("IPFS upload failed: {}", e);
            None
        }
    };

    // 3. Execute On-Chain Transfer
    let tx_hash = match contract.transfer(pk, &req.to, req.amount).await {
        Ok(hash) => hash,
        Err(e) => return HttpResponse::InternalServerError().json(json!({"error": format!("Blockchain tx failed: {}", e)})),
    };

    // 4. Save transaction record (Pending)
    // We do NOT update balances here. Event Listener will do it.
    let tx = Transaction {
        id: tx_hash.clone(), // Use Chain Tx Hash as ID
        from: req.from.clone(),
        to: req.to.clone(),
        amount: req.amount,
        status: "pending".to_string(),
        ipfs_cid: ipfs_cid.clone(),
    };

    if let Err(e) = dtl_infra::db::save_transaction(pool.get_ref(), &tx).await {
        println!("Failed to save transaction: {}", e);
    }

    HttpResponse::Ok().json(TransferResponse {
        status: "submitted".to_string(),
        tx_id: tx_hash,
        ipfs_cid,
    })
}
