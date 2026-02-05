# Terraform File Structure

Quick reference for the dependency-ordered file structure.

## Visual Structure

**Note**: All `.tf` files are in the root `terraform/` directory. Terraform only reads files from the directory where `terraform init` is run. The numbered prefixes organize files by dependency layer.

```
terraform/
│
├── 01-foundation.tf                    [No dependencies]
│   ├── Data sources
│   ├── Random suffix
│   └── Locals
│
├── 02-container-registry.tf            [→ 01-foundation.tf]
├── 02-key-vault.tf                    [→ 01-foundation.tf] Infrastructure only
├── 02-storage.tf                      [→ 01-foundation.tf] Infrastructure only
│
├── 03-identity.tf                     [→ 02-key-vault.tf, 02-container-registry.tf]
│
├── 04-container-mcp-search.tf        [→ Key Vault, ACR, Identity]
│   ├── MCP Search container config
│   └── Key Vault secrets (all app secrets)
├── 04-container-caddy.tf             [→ Storage Account]
│   ├── Caddy container config
│   └── File shares (caddy_data, caddy_config)
└── 04-container-group.tf             [→ All previous files]
    └── Container group (assembles all containers)
│
└── Configuration Files
    ├── providers.tf
    ├── variables.tf
    └── outputs.tf
```

## Quick Reference

| Directory | Layer | Files |
|-----------|-------|-------|
| `01-foundation/` | Layer 0 | `01-foundation.tf` |
| `02-core-infrastructure/` | Layer 1 | `02-container-registry.tf`, `02-key-vault.tf`, `02-storage.tf` |
| `03-identity/` | Layer 2 | `03-identity.tf` |
| `04-containers/` | Layer 3 | `04-container-mcp-search.tf`, `04-container-caddy.tf`, `04-container-group.tf` |

## Dependency Flow

```
01-foundation/01-foundation.tf
    │
    ├─→ 02-core-infrastructure/02-container-registry.tf ──┐
    ├─→ 02-core-infrastructure/02-key-vault.tf ───────────┼─→ 03-identity/03-identity.tf ──┐
    └─→ 02-core-infrastructure/02-storage.tf ──────────────┼───────────────────────────────┼─→ 04-containers/04-container-group.tf
                                                             │                             │   │
                                                             ├───────────────────────────────┼───┤
                                                             │                             │   │
                                                             └─→ 04-containers/04-container-mcp-search.tf (secrets)
                                                             └─→ 04-containers/04-container-caddy.tf (file shares)
```

**Key Principle**: Each container is self-contained in its own file - it defines its own file shares and secrets. Infrastructure (Key Vault, Storage Account) only needs to exist. The container group assembles all containers together.

## File Explorer View

When viewing in a file explorer, files are automatically sorted by prefix:

```
terraform/
├── 01-foundation.tf
├── 02-container-registry.tf
├── 02-key-vault.tf
├── 02-storage.tf
├── 03-identity.tf
├── 04-container-caddy.tf
├── 04-container-group.tf
├── 04-container-mcp-search.tf
├── providers.tf
├── variables.tf
└── outputs.tf
```

This makes it immediately clear which layer each file belongs to! The numbered prefixes create a visual dependency hierarchy even though all files are in the same directory.

## Architecture Benefits

✅ **Organized by dependency layers**: Folders reflect the dependency hierarchy  
✅ **One file per container**: Each container is completely self-contained  
✅ **Self-contained containers**: Each container defines its own file shares and secrets  
✅ **Clear separation**: Infrastructure (Key Vault, Storage) vs. Application resources  
✅ **Modular**: Easy to add new containers - just create a new file in `04-containers/`  
✅ **Self-documenting**: See exactly what a container needs in one file  
✅ **Easy to understand**: Container group file shows how containers are assembled  
✅ **Terraform-friendly**: Terraform reads all `.tf` files recursively, so this structure works seamlessly
