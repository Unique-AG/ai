# search-proxy

![Version: 2026.32.0](https://img.shields.io/badge/Version-2026.32.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 2026.32.0](https://img.shields.io/badge/AppVersion-2026.32.0-informational?style=flat-square)

Dedicated Helm chart for the Unique search proxy connector

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| oci://ghcr.io/unique-ag/helm | base | 0.1.0-eeb8aa |

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| autoscaling.enabled | bool | `false` |  |
| bingAgent.connection.azureIdentityCredentialType | string | `"default"` |  |
| bingAgent.connection.azureIdentityValidateTokenUrl | string | `"https://management.azure.com/.default"` |  |
| bingAgent.connection.cleanupOnStart | bool | `false` |  |
| bingAgent.connection.usePrivateEndpointTransport | bool | `false` |  |
| bingAgent.enabled | bool | `false` |  |
| braveSearch.connection.apiEndpoint | string | `"https://api.search.brave.com/res/v1/web/search"` |  |
| braveSearch.enabled | bool | `false` |  |
| deployment.metadata.annotations."reloader.stakater.com/auto" | string | `"true"` |  |
| deployment.revisionHistoryLimit | int | `3` |  |
| env.LOG_LEVEL | string | `"info"` |  |
| env.TIMEOUT | string | `"120"` |  |
| env.WORKERS | string | `"4"` |  |
| firecrawl.connection.apiEndpoint | string | `"https://api.firecrawl.dev"` |  |
| firecrawl.connection.apiVersion | string | `"v2"` |  |
| firecrawl.enabled | bool | `false` |  |
| fullnameOverride | string | `"search-proxy"` |  |
| googleSearch.connection.apiEndpoint | string | `"https://www.googleapis.com/customsearch/v1"` |  |
| googleSearch.enabled | bool | `false` |  |
| grafana.dashboards.enabled | bool | `true` |  |
| grafana.dashboards.replacements.%%PROMETHEUS_UID%% | string | `"prometheus"` |  |
| httpClient.connection.proxyAuthMode | string | `"none"` |  |
| httpClient.connection.proxyProtocol | string | `"http"` |  |
| httpClient.tuning.maxConnections | int | `100` |  |
| httpClient.tuning.maxKeepaliveConnections | int | `20` |  |
| httpClient.tuning.poolTimeoutSeconds | float | `30` |  |
| image.pullPolicy | string | `"IfNotPresent"` |  |
| image.registry | string | `"ghcr.io"` |  |
| image.repository | string | `"unique-ag/ai/search-proxy"` |  |
| image.tag | string | `"2026.32.0"` |  |
| image.useDigest | bool | `false` |  |
| jina.connection.apiDomain | string | `"jina.ai"` |  |
| jina.connection.deployment | string | `"global"` |  |
| jina.enabled | bool | `false` |  |
| nameOverride | string | `"search-proxy"` |  |
| networkPolicy.enableDefaultDeny.egress | bool | `true` |  |
| networkPolicy.enableDefaultDeny.ingress | bool | `true` |  |
| networkPolicy.enabled | bool | `false` |  |
| networkPolicy.flavor | string | `"cilium"` |  |
| pdb.maxUnavailable | string | `"30%"` |  |
| perplexitySearch.connection.apiEndpoint | string | `"https://api.perplexity.ai/search"` |  |
| perplexitySearch.enabled | bool | `false` |  |
| podSecurityContext.runAsNonRoot | bool | `true` |  |
| podSecurityContext.runAsUser | int | `1000` |  |
| podSecurityContext.seccompProfile.type | string | `"RuntimeDefault"` |  |
| ports.application | int | `8080` |  |
| probes.enabled | bool | `true` |  |
| probes.liveness.failureThreshold | int | `6` |  |
| probes.liveness.httpGet.path | string | `"/health"` |  |
| probes.liveness.httpGet.port | string | `"http"` |  |
| probes.liveness.initialDelaySeconds | int | `10` |  |
| probes.liveness.periodSeconds | int | `5` |  |
| probes.readiness.failureThreshold | int | `6` |  |
| probes.readiness.httpGet.path | string | `"/health"` |  |
| probes.readiness.httpGet.port | string | `"http"` |  |
| probes.readiness.initialDelaySeconds | int | `10` |  |
| probes.readiness.periodSeconds | int | `5` |  |
| probes.startup.failureThreshold | int | `30` |  |
| probes.startup.httpGet.path | string | `"/health"` |  |
| probes.startup.httpGet.port | string | `"http"` |  |
| probes.startup.initialDelaySeconds | int | `10` |  |
| probes.startup.periodSeconds | int | `10` |  |
| resources.limits.memory | string | `"384Mi"` |  |
| resources.requests.cpu | string | `"100m"` |  |
| resources.requests.memory | string | `"256Mi"` |  |
| securityContext.allowPrivilegeEscalation | bool | `false` |  |
| securityContext.capabilities.drop[0] | string | `"ALL"` |  |
| securityContext.readOnlyRootFilesystem | bool | `true` |  |
| securityContext.runAsNonRoot | bool | `true` |  |
| securityContext.runAsUser | int | `1000` |  |
| selectorComponentLabel | string | `"server"` |  |
| service.port | int | `80` |  |
| serviceAccount.enabled | bool | `true` |  |
| tavily.connection.apiEndpoint | string | `"https://api.tavily.com"` |  |
| tavily.enabled | bool | `false` |  |
| urlSafety.enabled | bool | `true` |  |
| urlSafety.network.allowedSchemes[0] | string | `"http"` |  |
| urlSafety.network.allowedSchemes[1] | string | `"https"` |  |
| urlSafety.network.clusterLocalSuffix | string | `".cluster.local"` |  |
| urlSafety.network.localhostHosts[0] | string | `"localhost"` |  |
| urlSafety.network.localhostHosts[1] | string | `"localhost.localdomain"` |  |
| urlSafety.network.metadataHosts[0] | string | `"100.100.100.200"` |  |
| urlSafety.network.metadataHosts[1] | string | `"169.254.169.254"` |  |
| urlSafety.network.metadataHosts[2] | string | `"169.254.170.2"` |  |
| urlSafety.network.metadataHosts[3] | string | `"metadata.azure.internal"` |  |
| urlSafety.network.metadataHosts[4] | string | `"metadata.google.internal"` |  |
| urlSafety.network.serviceSuffix | string | `".svc"` |  |
| urlSafety.redirects.maxRedirectHops | int | `10` |  |
| urlSafety.redirects.redirectTimeoutSeconds | float | `10` |  |
| urlSafety.redirects.resolveRedirects | bool | `true` |  |
| vertexaiAgent.connection.credentialType | string | `"workload_identity"` |  |
| vertexaiAgent.connection.serviceAccountScopes[0] | string | `"https://www.googleapis.com/auth/cloud-platform"` |  |
| vertexaiAgent.enabled | bool | `false` |  |
| volumeMounts[0].mountPath | string | `"/tmp"` |  |
| volumeMounts[0].name | string | `"tmp-volume"` |  |
| volumes[0].emptyDir.sizeLimit | string | `"5Gi"` |  |
| volumes[0].name | string | `"tmp-volume"` |  |
| workloadIdentity.gcp.enabled | bool | `false` |  |
| workloadIdentity.gcp.projectId | string | `""` |  |
| workloadIdentity.gcp.provider | string | `""` |  |
| workloadIdentity.gcp.serviceAccountEmail | string | `""` |  |
| workloadIdentity.gcp.workloadIdentityPool | string | `""` |  |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)
