output "db_connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${digitalocean_database_user.app_user.name}:${digitalocean_database_user.app_user.password}@${digitalocean_database_cluster.postgres.host}:${digitalocean_database_cluster.postgres.port}/${digitalocean_database_db.app_db.name}?sslmode=require"
  sensitive   = true
}

output "spaces_endpoint" {
  description = "DigitalOcean Spaces endpoint"
  value       = "https://${digitalocean_spaces_bucket.storage.region}.digitaloceanspaces.com"
}

output "spaces_bucket_name" {
  description = "Spaces bucket name"
  value       = digitalocean_spaces_bucket.storage.name
}

output "db_host" {
  description = "Database host"
  value       = digitalocean_database_cluster.postgres.host
}
