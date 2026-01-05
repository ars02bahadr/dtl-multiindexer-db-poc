use actix_web::{web, App, HttpServer, Responder, HttpResponse};
use actix_cors::Cors;
use dtl_infra::db::init_pool;
use tracing::info;

mod auth;
mod handlers;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    tracing_subscriber::fmt::init();

    info!("Starting DTL API server...");

    let pool = init_pool().await.expect("Failed to initialize database pool");

    HttpServer::new(move || {
        let cors = Cors::permissive();

        App::new()
            .wrap(cors)
            .app_data(web::Data::new(pool.clone()))
            .route("/health", web::get().to(health_check))
            .route("/users", web::get().to(handlers::get_users))
            .route("/seed", web::post().to(handlers::seed_users))
            .route("/transfer", web::post().to(handlers::transfer))
    })
    .bind(("127.0.0.1", 3000))?
    .run()
    .await
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}
