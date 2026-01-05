use ethers::prelude::*;
use std::sync::Arc;
use tracing::{info, error};

// Minimal ERC20 Event ABI
abigen!(
    MoneyToken,
    r#"[
        event Transfer(address indexed from, address indexed to, uint256 value)
    ]"#
);

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    info!("Starting Event Listener...");

    let pool = dtl_infra::db::init_pool().await.expect("Failed to create pool");

    let provider = dtl_infra::blockchain::init_ws_provider().await.map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;
    let client = Arc::new(provider);

    info!("Connected to Besu WS");

    let contract_addr = "0xa5A19a794fc1ec3010F832Dee431cF81D55D7Aee".parse::<Address>()?;
    let filter = Filter::new()
        .address(contract_addr)
        .event("Transfer(address,address,uint256)");

    let mut stream = client.subscribe_logs(&filter).await?;

    while let Some(log) = stream.next().await {
        info!("Received log: {:?}", log);

        // Parse log
        if let Ok(event) = parse_log::<TransferFilter>(log.clone()) {
            info!("Decoded Transfer: from={:?}, to={:?}, value={}", event.from, event.to, event.value);

            let from_addr = format!("{:?}", event.from);
            let to_addr = format!("{:?}", event.to);
            let amount = event.value.as_u64(); // Simplified for PoC

            // 1. Update DB Balances
            if let Err(e) = dtl_infra::db::transfer(&pool, &from_addr, &to_addr, amount).await {
                error!("Failed to sync transfer to DB: {}", e);
            } else {
                info!("Synced transfer to DB: {} -> {} ({})", from_addr, to_addr, amount);
            }

            // 2. Update Transaction Status
            let tx_hash = format!("{:?}", log.transaction_hash.unwrap_or_default());
            let tx = dtl_domain::Transaction {
                id: tx_hash.clone(),
                from: from_addr,
                to: to_addr,
                amount,
                status: "confirmed".to_string(),
                ipfs_cid: None, // Cannot retrieve from log easily, assuming API set it
            };

            if let Err(e) = dtl_infra::db::save_transaction(&pool, &tx).await {
                 error!("Failed to save transaction status: {}", e);
            }
        }
    }

    Ok(())
}
