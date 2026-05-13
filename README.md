# AI Infoline

AI-alapú telefonos infoline SaaS platform.

## Stack

| Réteg | Technológia |
|-------|-------------|
| IaC | Terraform (DigitalOcean) |
| Backend | Python / FastAPI |
| Adatbázis | DigitalOcean Managed PostgreSQL |
| Fájltárolás | DigitalOcean Spaces |
| Konténerizáció | Docker / docker-compose |

## Projekt struktúra

```
ai-infoline/
├── api/                  # FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # Frontend (placeholder)
├── terraform/            # Infrastructure as Code
│   ├── providers.tf
│   ├── variables.tf
│   ├── database.tf       # DO Managed PostgreSQL
│   ├── spaces.tf         # DO Spaces bucket
│   └── outputs.tf
├── docker-compose.yml    # Helyi fejlesztés
├── .env.example
└── .gitignore
```

## Helyi fejlesztés

```bash
cp .env.example .env
# Töltsd ki a .env értékeit

docker-compose up
```

Az API elérhető: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

## Infrastructure (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Töltsd ki a terraform.tfvars értékeit

terraform init
terraform plan
terraform apply
```

A Terraform **csak** a következőket kezeli:
- DO Managed PostgreSQL cluster (`db-s-1vcpu-1gb`)
- DO Spaces bucket

A meglévő Droplet **nem** Terraform-managed.

## Külső szolgáltatások

| Szolgáltatás | Célra |
|---|---|
| Anthropic | LLM (Claude) |
| Deepgram | Speech-to-text |
| Twilio | Telefonhívások kezelése |
| Stripe | Fizetések |
