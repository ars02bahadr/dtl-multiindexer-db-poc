use ethers::prelude::*;
use std::sync::Arc;
use std::convert::TryFrom;
use std::str::FromStr;

// Minimal ERC20 ABI for transfer
abigen!(
    MoneyToken,
    r#"[
        function transfer(address to, uint256 amount) external returns (bool)
        function balanceOf(address account) external view returns (uint256)
    ]"#
);

pub struct MoneyTokenContract {
    contract_address: Address,
    provider: Provider<Http>,
    chain_id: u64,
}

impl MoneyTokenContract {
    pub fn new(address: &str, provider_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let provider = Provider::<Http>::try_from(provider_url)?;
        let contract_address = Address::from_str(address)?;

        Ok(Self {
            contract_address,
            provider,
            chain_id: 1337, // Besu dev chain ID
        })
    }

    pub async fn transfer(
        &self,
        from_private_key: &str,
        to_address: &str,
        amount: u64, // Amount in units (not wei, assuming we handle decimals elsewhere or 1:1)
    ) -> Result<String, Box<dyn std::error::Error>> {
        let wallet: LocalWallet = from_private_key.parse::<LocalWallet>()?.with_chain_id(self.chain_id);
        let client = SignerMiddleware::new(self.provider.clone(), wallet);
        let client = Arc::new(client);

        let contract = MoneyToken::new(self.contract_address, client);

        let to = Address::from_str(to_address)?;
        let amount_u256 = U256::from(amount); // Assuming simple unit for PoC

        let call = contract.transfer(to, amount_u256).legacy();
        let tx = call.send().await?;
        let receipt = tx.await?;

        match receipt {
            Some(r) => Ok(format!("{:?}", r.transaction_hash)),
            None => Err("Transaction failed (no receipt)".into()),
        }
    }
}
