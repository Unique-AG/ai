# ============================================================================
# Caddy Reverse Proxy Container
# Depends on: foundation.tf, storage.tf
# 
# This file defines everything the Caddy container needs:
# - File shares it uses
# - Container configuration
# ============================================================================

# ----------------------------------------------------------------------------
# File Shares (defined by this container)
# ----------------------------------------------------------------------------

resource "azurerm_storage_share" "caddy_data_prod" {
  name               = "caddy-data-prod"
  storage_account_id = azurerm_storage_account.main.id
  quota              = 1 # GB
}

resource "azurerm_storage_share" "caddy_data_staging" {
  name               = "caddy-data-staging"
  storage_account_id = azurerm_storage_account.main.id
  quota              = 1 # GB
}

resource "azurerm_storage_share" "caddy_config" {
  name               = "caddy-config"
  storage_account_id = azurerm_storage_account.main.id
  quota              = 1 # GB
}


# ----------------------------------------------------------------------------
# Container Configuration (as local for reference in container group)
# ----------------------------------------------------------------------------

locals {
  # Determine which template and file share to use based on use_staging_letsencrypt
  caddy_template_file = var.use_staging_letsencrypt ? "Caddyfile.staging.template" : "Caddyfile.prod.template"
  caddy_data_share    = var.use_staging_letsencrypt ? azurerm_storage_share.caddy_data_staging : azurerm_storage_share.caddy_data_prod

  # Render the Caddyfile template
  caddyfile_content = templatefile(
    "${path.module}/${local.caddy_template_file}",
    {
      domain_name = var.domain_name
      caddy_email = var.caddy_email
    }
  )

  # Base64 encode the Caddyfile content for safe transmission via environment variable
  caddyfile_content_b64 = base64encode(local.caddyfile_content)

  caddy_container = {
    name   = "caddy"
    image  = "caddy:2-alpine"
    cpu    = var.caddy_container_cpu
    memory = var.caddy_container_memory

    ports = [
      {
        port     = 80
        protocol = "TCP"
      },
      {
        port     = 443
        protocol = "TCP"
      }
    ]

    environment_variables = {
      "DOMAIN_NAME"             = var.domain_name
      "CADDY_EMAIL"             = var.caddy_email
      "USE_STAGING_LETSENCRYPT" = var.use_staging_letsencrypt ? "true" : "false"
      "CADDYFILE_CONTENT_B64"   = local.caddyfile_content_b64
    }

    commands = [
      "sh",
      "-c",
      <<-EOF
        echo "=========================================="
        echo "Caddy Configuration"
        echo "=========================================="
        echo "Domain: $${DOMAIN_NAME}"
        echo "Email: $${CADDY_EMAIL}"
        echo "Let's Encrypt Environment: $${USE_STAGING_LETSENCRYPT}"
        if [ "$${USE_STAGING_LETSENCRYPT}" = "true" ]; then
          echo "Using Let's Encrypt STAGING (certificates NOT trusted)"
        else
          echo "Using Let's Encrypt PRODUCTION (trusted certificates)"
        fi
        echo "=========================================="
        echo ""
        
        # Decode and write the Caddyfile from template (rendered by Terraform)
        # Using base64 encoding to safely pass multi-line content via environment variable
        echo "$${CADDYFILE_CONTENT_B64}" | base64 -d > /etc/caddy/Caddyfile
        
        echo "Caddyfile generated from template:"
        cat /etc/caddy/Caddyfile
        echo ""
        echo "Starting Caddy..."
        
        caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
      EOF
    ]

    volumes = [
      {
        name                 = var.use_staging_letsencrypt ? "caddy-data-staging" : "caddy-data-prod"
        mount_path           = "/data"
        storage_account_name = azurerm_storage_account.main.name
        storage_account_key  = azurerm_storage_account.main.primary_access_key
        share_name           = local.caddy_data_share.name
      },
      {
        name                 = "caddy-config"
        mount_path           = "/config"
        storage_account_name = azurerm_storage_account.main.name
        storage_account_key  = azurerm_storage_account.main.primary_access_key
        share_name           = azurerm_storage_share.caddy_config.name
      }
    ]
  }
}
