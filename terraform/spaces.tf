resource "digitalocean_spaces_bucket" "storage" {
  name   = "${var.project_name}-storage"
  region = var.region
  acl    = "private"

  versioning {
    enabled = true
  }
}
