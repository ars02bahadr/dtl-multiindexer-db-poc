use reqwest::Client;
use serde_json::json;

const IPFS_API_URL: &str = "http://127.0.0.1:5001/api/v0";

pub async fn upload_json(data: &serde_json::Value) -> Result<String, Box<dyn std::error::Error>> {
    let client = Client::new();

    let json_str = serde_json::to_string(data)?;

    let form = reqwest::multipart::Form::new()
        .text("file", json_str);

    let response = client
        .post(format!("{}/add", IPFS_API_URL))
        .multipart(form)
        .send()
        .await?;

    let result: serde_json::Value = response.json().await?;
    let cid = result["Hash"].as_str().unwrap_or("").to_string();

    Ok(cid)
}

pub async fn get_json(cid: &str) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
    let client = Client::new();

    let response = client
        .post(format!("{}/cat?arg={}", IPFS_API_URL, cid))
        .send()
        .await?;

    let data: serde_json::Value = response.json().await?;
    Ok(data)
}
