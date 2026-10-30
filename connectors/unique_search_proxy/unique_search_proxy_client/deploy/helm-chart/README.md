# search-proxy

![Version: 2026.44.0](https://img.shields.io/badge/Version-2026.44.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 2026.44.0](https://img.shields.io/badge/AppVersion-2026.44.0-informational?style=flat-square)

Dedicated Helm chart for the Unique search proxy connector

## Network access

search-proxy has no caller authentication. It is internal-only: do not add an Ingress, Gateway route or any other route to it. The Cilium network policy is the only control on who can reach it, so it is on by default.

- Ingress is limited to Prometheus (namespace `system`) and assistants-core, which every caller goes through. assistants-core is expected in the `chat` namespace. Where it runs elsewhere, set `internalServices.dependents.assistantsCore.namespace`. Add further callers as extra `internalServices.dependents` entries. The base chart also admits return traffic from the internet on ephemeral ports (32768-60999); nothing listens there.
- Egress is limited to DNS, the FQDNs of the enabled providers, the corporate proxy host and port when `httpClient.connection.proxyHost` and `proxyPort` are set (an in-cluster proxy is not covered), and ports 443 and 80 to the internet for crawling (the `networkPolicy.baseline.egress.worldHttp` rule). `urlSafety` rejects internal crawl targets.
- Link-local addresses (`169.254.0.0/16`, the cloud metadata service) are denied through `networkPolicy.egressDeny`. Helm replaces lists, so an overlay that sets its own `egressDeny` must repeat this entry.
- Strict proxy mode is only for tenants that must send all traffic through a corporate proxy. Set `networkPolicy.baseline.egress.worldHttp.enabled: false`, which requires the proxy host and port. This removes the open internet rule only: enabled providers keep their FQDN rules. Bing and the Azure workload identity login then need their Entra login hosts, and Vertex AI its GCP hosts, added as FQDN rules in the overlay.
- `networkPolicy.enabled: false` fails the render unless `networkPolicy.allowDisabled: true` is also set. Set that only when another control restricts who can reach search-proxy.
- Cilium is required. On a cluster without the Cilium CRDs the install fails. That is intended (fail-closed). `flavor: kubernetes` is not supported by this chart.

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| oci://ghcr.io/unique-ag/helm | base | 0.1.0-7ddb46 |

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
| env.WORKERS | string | `"2"` |  |
| firecrawl.connection.apiEndpoint | string | `"https://api.firecrawl.dev"` |  |
| firecrawl.connection.apiVersion | string | `"v2"` |  |
| firecrawl.enabled | bool | `false` |  |
| fullnameOverride | string | `"search-proxy"` |  |
| googleSearch.connection.apiEndpoint | string | `"https://www.googleapis.com/customsearch/v1"` |  |
| googleSearch.enabled | bool | `false` |  |
| grafana.dashboards.enabled | bool | `true` |  |
| grafana.dashboards.replacements.%%PROMETHEUS_UID%% | string | `"prometheus"` |  |
| httpClient.connection.perUserProxyCompanyIds | list | `[]` |  |
| httpClient.connection.proxyAuthMode | string | `"none"` |  |
| httpClient.connection.proxyProtocol | string | `"http"` |  |
| httpClient.connection.proxyUsernameMetadataField | string | `"userName"` |  |
| httpClient.connection.proxyUsernameSource | string | `"settings"` |  |
| httpClient.tuning.httpClientCacheSize | int | `128` |  |
| httpClient.tuning.maxConnections | int | `100` |  |
| httpClient.tuning.maxKeepaliveConnections | int | `20` |  |
| httpClient.tuning.maxResponseKib | int | `5120` |  |
| httpClient.tuning.poolTimeoutSeconds | float | `30` |  |
| image.pullPolicy | string | `"IfNotPresent"` |  |
| image.registry | string | `"ghcr.io"` |  |
| image.repository | string | `"unique-ag/ai/search-proxy"` |  |
| image.tag | string | `"2026.44.0"` |  |
| image.useDigest | bool | `false` |  |
| internalServices.dependents.assistantsCore.name | string | `"assistants-core"` |  |
| internalServices.dependents.assistantsCore.namespace | string | `"chat"` |  |
| jina.connection.apiDomain | string | `"jina.ai"` |  |
| jina.connection.deployment | string | `"global"` |  |
| jina.enabled | bool | `false` |  |
| nameOverride | string | `"search-proxy"` |  |
| networkPolicy.allowDisabled | bool | `false` | Set true only if another control restricts who can reach search-proxy. |
| networkPolicy.baseline.egress.worldHttp | object | `{"toEntities":["world"],"toPorts":[{"ports":[{"port":"443","protocol":"TCP"},{"port":"80","protocol":"TCP"}]}]}` | Ports 443 and 80 to the internet for crawling. Set `enabled: false` only for corporate-proxy tenants (needs a proxy host and port). Enabled providers keep their FQDN rules; Bing, Vertex AI and the Azure workload identity login then need their own rules. |
| networkPolicy.baseline.prometheus.namespace | string | `"system"` |  |
| networkPolicy.egressDeny | list | `[{"toCIDR":["169.254.0.0/16"]}]` | Blocks link-local addresses (cloud metadata service, IMDS) even though world egress is allowed. Deny rules win over allow rules. |
| networkPolicy.enableDefaultDeny.egress | bool | `true` |  |
| networkPolicy.enableDefaultDeny.ingress | bool | `true` |  |
| networkPolicy.enabled | bool | `true` | Rendering fails when false unless `allowDisabled` is true. |
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
| replicaCount | int | `1` | Use at least 2 in production. |
| requestLimits.crawl.maxConcurrentCrawls | int | `4` |  |
| requestLimits.crawl.maxConcurrentFetches | int | `10` |  |
| requestLimits.crawl.maxCrawlResponseKib | int | `10240` |  |
| requestLimits.crawl.maxUrlLength | int | `2048` |  |
| requestLimits.crawl.maxUrlsPerCrawl | int | `100` |  |
| requestLimits.timeouts.maxTimeoutSeconds | int | `120` |  |
| resources.limits.memory | string | `"4Gi"` |  |
| resources.requests.cpu | string | `"1"` |  |
| resources.requests.memory | string | `"2Gi"` |  |
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
| urlSafety.network.customApiTrustedPrivateHosts | list | `[]` |  |
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
