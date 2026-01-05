use ethers::prelude::*;
use std::env;

pub type EthClient = SignerMiddleware<Provider<Http>, LocalWallet>;

pub async fn init_provider() -> Result<Provider<Http>, ProviderError> {
    let rpc_url = env::var("RPC_URL").unwrap_or_else(|_| "http://localhost:8545".to_string());
    let provider = Provider::<Http>::try_from(rpc_url).map_err(|e| ProviderError::CustomError(e.to_string()))?;
    Ok(provider)
}

pub async fn init_ws_provider() -> Result<Provider<Ws>, ProviderError> {
    let ws_url = env::var("WS_URL").unwrap_or_else(|_| "ws://localhost:8546".to_string());
    Provider::<Ws>::connect(ws_url).await.map_err(|e| ProviderError::CustomError(e.to_string()))
}
