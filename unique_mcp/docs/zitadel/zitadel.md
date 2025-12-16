# Zitadel 


# Architecture of Zitadel

```mermaid
flowchart TD

    %% Top level
    I[1️⃣ Instance]

    %% Organization level
    subgraph ORG[2️⃣ Organization]
        direction TB
        U[Users<br/>Managed at Organization level]
        P[Projects<br/>Exist at Organization level]
    end

    %% Project contents
    subgraph PROJ[Project Structure]
        direction TB
        A[Apps<br/>OIDC / SAML Clients]
        R[Roles<br/>Defined per Project]
        AP[Authorization Policies<br/>Based on Roles]
    end

    %% Hierarchy links
    I --> ORG
    ORG --> U
    ORG --> P
    P --> PROJ

    %% Relationships
    U -->|assigned project roles| R
    R -->|used in| AP
    AP -->|governs access to| A

```

# Secrets per APP

The following secrets are required in a environement file calle `zitadel.env`

```
ZITADEL_URL=
UPSTREAM_CLIENT_ID=
UPSTREAM_CLIENT_SECRET=
```

after setting up an App they can be found



