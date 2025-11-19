# Policy pour Jenkins - Lecture seule
path "secret/data/*" {
  capabilities = ["read", "list"]
}

path "pki/issue/*" {
  capabilities = ["create", "update"]
}