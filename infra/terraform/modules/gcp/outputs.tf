output "service_account_email" {
  value = google_service_account.app.email
}

output "cloud_run_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "database_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "redis_host" {
  value = google_redis_instance.main.host
}

output "redis_port" {
  value = google_redis_instance.main.port
}
