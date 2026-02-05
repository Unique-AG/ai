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

resource "azurerm_storage_share" "caddy_data" {
  name               = "caddy-data"
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
      "DOMAIN_NAME" = var.domain_name
      "CADDY_EMAIL" = var.caddy_email
    }

    commands = [
      "sh",
      "-c",
      <<-EOF
        cat > /etc/caddy/Caddyfile << CADDYFILE
        {
            email $${CADDY_EMAIL}
            # Disable automatic HTTPS for testing (enable when DNS is configured)
            auto_https disable_redirects
        }

        # Serve domain (HTTPS when DNS configured, HTTP fallback)
        $${DOMAIN_NAME} {
            reverse_proxy localhost:8000

            header {
                X-Content-Type-Options nosniff
                X-Frame-Options DENY
                Referrer-Policy strict-origin-when-cross-origin
            }

            log {
                output stdout
                format json
            }
        }

        # Serve HTTP on port 80 for any host (testing without DNS)
        :80 {
            reverse_proxy localhost:8000

            header {
                X-Content-Type-Options nosniff
                X-Frame-Options DENY
                Referrer-Policy strict-origin-when-cross-origin
            }

            log {
                output stdout
                format json
            }
        }
        CADDYFILE
        caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
      EOF
    ]

    volumes = [
      {
        name                 = "caddy-data"
        mount_path           = "/data"
        storage_account_name = azurerm_storage_account.main.name
        storage_account_key  = azurerm_storage_account.main.primary_access_key
        share_name           = azurerm_storage_share.caddy_data.name
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
