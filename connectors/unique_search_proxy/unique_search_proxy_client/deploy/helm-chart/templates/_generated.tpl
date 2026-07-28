{{/*
GENERATED — do not edit. Regenerate with:
  uv run python scripts/generate_helm_config.py

Generated Helm wiring for every @helm_settings group (search providers plus
internal config such as httpClient and urlSafety): env injection, Cilium egress
rules and secret-provider collection. Implemented as overrides of the shared base
library extension hooks (base.externalService.*.ext).
*/}}
{{- define "base.externalService.env.ext" -}}
{{- if and .Values.googleSearch .Values.googleSearch.enabled }}
{{- if not .Values.googleSearch.connection.apiKey }}
{{- fail "googleSearch.connection.apiKey is required when googleSearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "GOOGLE_SEARCH_API_KEY" "src" .Values.googleSearch.connection.apiKey "ctx" .) }}
- name: GOOGLE_SEARCH_API_ENDPOINT
  value: {{ .Values.googleSearch.connection.apiEndpoint | quote }}
- name: GOOGLE_SEARCH_ENGINE_ID
  value: {{ required "googleSearch.connection.engineId is required when googleSearch.enabled is true. Set it in your environment overlay." .Values.googleSearch.connection.engineId | quote }}
{{- end }}
{{- if and .Values.braveSearch .Values.braveSearch.enabled }}
{{- if not .Values.braveSearch.connection.apiKey }}
{{- fail "braveSearch.connection.apiKey is required when braveSearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BRAVE_SEARCH_API_KEY" "src" .Values.braveSearch.connection.apiKey "ctx" .) }}
- name: BRAVE_SEARCH_API_ENDPOINT
  value: {{ .Values.braveSearch.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .Values.perplexitySearch .Values.perplexitySearch.enabled }}
{{- if not .Values.perplexitySearch.connection.apiKey }}
{{- fail "perplexitySearch.connection.apiKey is required when perplexitySearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "PERPLEXITY_SEARCH_API_KEY" "src" .Values.perplexitySearch.connection.apiKey "ctx" .) }}
- name: PERPLEXITY_SEARCH_API_ENDPOINT
  value: {{ .Values.perplexitySearch.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .Values.bingAgent .Values.bingAgent.enabled }}
{{- if not .Values.bingAgent.connection.endpoint }}
{{- fail "bingAgent.connection.endpoint is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_ENDPOINT" "src" .Values.bingAgent.connection.endpoint "ctx" .) }}
{{- if not .Values.bingAgent.connection.bingResourceConnectionString }}
{{- fail "bingAgent.connection.bingResourceConnectionString is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_BING_RESOURCE_CONNECTION_STRING" "src" .Values.bingAgent.connection.bingResourceConnectionString "ctx" .) }}
{{- if .Values.bingAgent.connection.agentId }}
- name: BING_AGENT_AGENT_ID
  value: {{ .Values.bingAgent.connection.agentId | quote }}
{{- end }}
{{- if not .Values.bingAgent.connection.bingAgentModel }}
{{- fail "bingAgent.connection.bingAgentModel is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_BING_AGENT_MODEL" "src" .Values.bingAgent.connection.bingAgentModel "ctx" .) }}
- name: BING_AGENT_AZURE_IDENTITY_CREDENTIAL_TYPE
  value: {{ .Values.bingAgent.connection.azureIdentityCredentialType | quote }}
- name: BING_AGENT_AZURE_IDENTITY_VALIDATE_TOKEN_URL
  value: {{ .Values.bingAgent.connection.azureIdentityValidateTokenUrl | quote }}
- name: BING_AGENT_USE_PRIVATE_ENDPOINT_TRANSPORT
  value: {{ .Values.bingAgent.connection.usePrivateEndpointTransport | quote }}
- name: BING_AGENT_CLEANUP_ON_START
  value: {{ .Values.bingAgent.connection.cleanupOnStart | quote }}
{{- end }}
{{- if and .Values.vertexaiAgent .Values.vertexaiAgent.enabled }}
- name: VERTEXAI_AGENT_CREDENTIAL_TYPE
  value: {{ .Values.vertexaiAgent.connection.credentialType | quote }}
{{- if .Values.vertexaiAgent.connection.serviceAccountCredentials }}
{{ include "base.valueSource.env" (dict "name" "VERTEXAI_AGENT_SERVICE_ACCOUNT_CREDENTIALS" "src" .Values.vertexaiAgent.connection.serviceAccountCredentials "ctx" .) }}
{{- end }}
- name: VERTEXAI_AGENT_SERVICE_ACCOUNT_SCOPES
  value: {{ .Values.vertexaiAgent.connection.serviceAccountScopes | toJson | quote }}
{{- end }}
{{- if and .Values.tavily .Values.tavily.enabled }}
{{- if not .Values.tavily.connection.apiKey }}
{{- fail "tavily.connection.apiKey is required when tavily.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "TAVILY_API_KEY" "src" .Values.tavily.connection.apiKey "ctx" .) }}
- name: TAVILY_API_ENDPOINT
  value: {{ .Values.tavily.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .Values.jina .Values.jina.enabled }}
{{- if not .Values.jina.connection.apiKey }}
{{- fail "jina.connection.apiKey is required when jina.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "JINA_API_KEY" "src" .Values.jina.connection.apiKey "ctx" .) }}
- name: JINA_DEPLOYMENT
  value: {{ .Values.jina.connection.deployment | quote }}
- name: JINA_API_DOMAIN
  value: {{ .Values.jina.connection.apiDomain | quote }}
{{- end }}
{{- if and .Values.firecrawl .Values.firecrawl.enabled }}
{{- if not .Values.firecrawl.connection.apiKey }}
{{- fail "firecrawl.connection.apiKey is required when firecrawl.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "FIRECRAWL_API_KEY" "src" .Values.firecrawl.connection.apiKey "ctx" .) }}
- name: FIRECRAWL_API_ENDPOINT
  value: {{ .Values.firecrawl.connection.apiEndpoint | quote }}
- name: FIRECRAWL_API_VERSION
  value: {{ .Values.firecrawl.connection.apiVersion | quote }}
{{- end }}
- name: HTTP_CLIENT_PROXY_AUTH_MODE
  value: {{ .Values.httpClient.connection.proxyAuthMode | quote }}
- name: HTTP_CLIENT_PROXY_PROTOCOL
  value: {{ .Values.httpClient.connection.proxyProtocol | quote }}
{{- if .Values.httpClient.connection.proxyHost }}
- name: HTTP_CLIENT_PROXY_HOST
  value: {{ .Values.httpClient.connection.proxyHost | quote }}
{{- end }}
{{- if .Values.httpClient.connection.proxyPort }}
- name: HTTP_CLIENT_PROXY_PORT
  value: {{ .Values.httpClient.connection.proxyPort | quote }}
{{- end }}
{{- if .Values.httpClient.connection.proxySslCaBundlePath }}
- name: HTTP_CLIENT_PROXY_SSL_CA_BUNDLE_PATH
  value: {{ .Values.httpClient.connection.proxySslCaBundlePath | quote }}
{{- end }}
{{- if .Values.httpClient.connection.proxyUsername }}
{{ include "base.valueSource.env" (dict "name" "HTTP_CLIENT_PROXY_USERNAME" "src" .Values.httpClient.connection.proxyUsername "ctx" .) }}
{{- end }}
{{- if .Values.httpClient.connection.proxyPassword }}
{{ include "base.valueSource.env" (dict "name" "HTTP_CLIENT_PROXY_PASSWORD" "src" .Values.httpClient.connection.proxyPassword "ctx" .) }}
{{- end }}
{{- if .Values.httpClient.connection.proxySslCertPath }}
- name: HTTP_CLIENT_PROXY_SSL_CERT_PATH
  value: {{ .Values.httpClient.connection.proxySslCertPath | quote }}
{{- end }}
{{- if .Values.httpClient.connection.proxySslKeyPath }}
- name: HTTP_CLIENT_PROXY_SSL_KEY_PATH
  value: {{ .Values.httpClient.connection.proxySslKeyPath | quote }}
{{- end }}
- name: HTTP_CLIENT_POOL_TIMEOUT_SECONDS
  value: {{ .Values.httpClient.tuning.poolTimeoutSeconds | quote }}
- name: HTTP_CLIENT_MAX_CONNECTIONS
  value: {{ .Values.httpClient.tuning.maxConnections | quote }}
- name: HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS
  value: {{ .Values.httpClient.tuning.maxKeepaliveConnections | quote }}
- name: URL_SAFETY_ENABLED
  value: {{ .Values.urlSafety.enabled | quote }}
- name: URL_SAFETY_RESOLVE_REDIRECTS
  value: {{ .Values.urlSafety.redirects.resolveRedirects | quote }}
- name: URL_SAFETY_ALLOWED_SCHEMES
  value: {{ .Values.urlSafety.network.allowedSchemes | toJson | quote }}
- name: URL_SAFETY_LOCALHOST_HOSTS
  value: {{ .Values.urlSafety.network.localhostHosts | toJson | quote }}
- name: URL_SAFETY_METADATA_HOSTS
  value: {{ .Values.urlSafety.network.metadataHosts | toJson | quote }}
- name: URL_SAFETY_CLUSTER_LOCAL_SUFFIX
  value: {{ .Values.urlSafety.network.clusterLocalSuffix | quote }}
- name: URL_SAFETY_SERVICE_SUFFIX
  value: {{ .Values.urlSafety.network.serviceSuffix | quote }}
- name: URL_SAFETY_MAX_REDIRECT_HOPS
  value: {{ .Values.urlSafety.redirects.maxRedirectHops | quote }}
- name: URL_SAFETY_REDIRECT_TIMEOUT_SECONDS
  value: {{ .Values.urlSafety.redirects.redirectTimeoutSeconds | quote }}
{{- end -}}

{{- define "base.externalService.hooks.env.ext" -}}
{{- if and .ctx.Values.googleSearch .ctx.Values.googleSearch.enabled }}
{{- if not .ctx.Values.googleSearch.connection.apiKey }}
{{- fail "googleSearch.connection.apiKey is required when googleSearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "GOOGLE_SEARCH_API_KEY" "src" .ctx.Values.googleSearch.connection.apiKey "ctx" .ctx) }}
- name: GOOGLE_SEARCH_API_ENDPOINT
  value: {{ .ctx.Values.googleSearch.connection.apiEndpoint | quote }}
- name: GOOGLE_SEARCH_ENGINE_ID
  value: {{ required "googleSearch.connection.engineId is required when googleSearch.enabled is true. Set it in your environment overlay." .ctx.Values.googleSearch.connection.engineId | quote }}
{{- end }}
{{- if and .ctx.Values.braveSearch .ctx.Values.braveSearch.enabled }}
{{- if not .ctx.Values.braveSearch.connection.apiKey }}
{{- fail "braveSearch.connection.apiKey is required when braveSearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BRAVE_SEARCH_API_KEY" "src" .ctx.Values.braveSearch.connection.apiKey "ctx" .ctx) }}
- name: BRAVE_SEARCH_API_ENDPOINT
  value: {{ .ctx.Values.braveSearch.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .ctx.Values.perplexitySearch .ctx.Values.perplexitySearch.enabled }}
{{- if not .ctx.Values.perplexitySearch.connection.apiKey }}
{{- fail "perplexitySearch.connection.apiKey is required when perplexitySearch.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "PERPLEXITY_SEARCH_API_KEY" "src" .ctx.Values.perplexitySearch.connection.apiKey "ctx" .ctx) }}
- name: PERPLEXITY_SEARCH_API_ENDPOINT
  value: {{ .ctx.Values.perplexitySearch.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .ctx.Values.bingAgent .ctx.Values.bingAgent.enabled }}
{{- if not .ctx.Values.bingAgent.connection.endpoint }}
{{- fail "bingAgent.connection.endpoint is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_ENDPOINT" "src" .ctx.Values.bingAgent.connection.endpoint "ctx" .ctx) }}
{{- if not .ctx.Values.bingAgent.connection.bingResourceConnectionString }}
{{- fail "bingAgent.connection.bingResourceConnectionString is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_BING_RESOURCE_CONNECTION_STRING" "src" .ctx.Values.bingAgent.connection.bingResourceConnectionString "ctx" .ctx) }}
{{- if .ctx.Values.bingAgent.connection.agentId }}
- name: BING_AGENT_AGENT_ID
  value: {{ .ctx.Values.bingAgent.connection.agentId | quote }}
{{- end }}
{{- if not .ctx.Values.bingAgent.connection.bingAgentModel }}
{{- fail "bingAgent.connection.bingAgentModel is required when bingAgent.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "BING_AGENT_BING_AGENT_MODEL" "src" .ctx.Values.bingAgent.connection.bingAgentModel "ctx" .ctx) }}
- name: BING_AGENT_AZURE_IDENTITY_CREDENTIAL_TYPE
  value: {{ .ctx.Values.bingAgent.connection.azureIdentityCredentialType | quote }}
- name: BING_AGENT_AZURE_IDENTITY_VALIDATE_TOKEN_URL
  value: {{ .ctx.Values.bingAgent.connection.azureIdentityValidateTokenUrl | quote }}
- name: BING_AGENT_USE_PRIVATE_ENDPOINT_TRANSPORT
  value: {{ .ctx.Values.bingAgent.connection.usePrivateEndpointTransport | quote }}
- name: BING_AGENT_CLEANUP_ON_START
  value: {{ .ctx.Values.bingAgent.connection.cleanupOnStart | quote }}
{{- end }}
{{- if and .ctx.Values.vertexaiAgent .ctx.Values.vertexaiAgent.enabled }}
- name: VERTEXAI_AGENT_CREDENTIAL_TYPE
  value: {{ .ctx.Values.vertexaiAgent.connection.credentialType | quote }}
{{- if .ctx.Values.vertexaiAgent.connection.serviceAccountCredentials }}
{{ include "base.valueSource.env" (dict "name" "VERTEXAI_AGENT_SERVICE_ACCOUNT_CREDENTIALS" "src" .ctx.Values.vertexaiAgent.connection.serviceAccountCredentials "ctx" .ctx) }}
{{- end }}
- name: VERTEXAI_AGENT_SERVICE_ACCOUNT_SCOPES
  value: {{ .ctx.Values.vertexaiAgent.connection.serviceAccountScopes | toJson | quote }}
{{- end }}
{{- if and .ctx.Values.tavily .ctx.Values.tavily.enabled }}
{{- if not .ctx.Values.tavily.connection.apiKey }}
{{- fail "tavily.connection.apiKey is required when tavily.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "TAVILY_API_KEY" "src" .ctx.Values.tavily.connection.apiKey "ctx" .ctx) }}
- name: TAVILY_API_ENDPOINT
  value: {{ .ctx.Values.tavily.connection.apiEndpoint | quote }}
{{- end }}
{{- if and .ctx.Values.jina .ctx.Values.jina.enabled }}
{{- if not .ctx.Values.jina.connection.apiKey }}
{{- fail "jina.connection.apiKey is required when jina.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "JINA_API_KEY" "src" .ctx.Values.jina.connection.apiKey "ctx" .ctx) }}
- name: JINA_DEPLOYMENT
  value: {{ .ctx.Values.jina.connection.deployment | quote }}
- name: JINA_API_DOMAIN
  value: {{ .ctx.Values.jina.connection.apiDomain | quote }}
{{- end }}
{{- if and .ctx.Values.firecrawl .ctx.Values.firecrawl.enabled }}
{{- if not .ctx.Values.firecrawl.connection.apiKey }}
{{- fail "firecrawl.connection.apiKey is required when firecrawl.enabled is true. Set it in your environment overlay." }}
{{- end }}
{{ include "base.valueSource.env" (dict "name" "FIRECRAWL_API_KEY" "src" .ctx.Values.firecrawl.connection.apiKey "ctx" .ctx) }}
- name: FIRECRAWL_API_ENDPOINT
  value: {{ .ctx.Values.firecrawl.connection.apiEndpoint | quote }}
- name: FIRECRAWL_API_VERSION
  value: {{ .ctx.Values.firecrawl.connection.apiVersion | quote }}
{{- end }}
- name: HTTP_CLIENT_PROXY_AUTH_MODE
  value: {{ .ctx.Values.httpClient.connection.proxyAuthMode | quote }}
- name: HTTP_CLIENT_PROXY_PROTOCOL
  value: {{ .ctx.Values.httpClient.connection.proxyProtocol | quote }}
{{- if .ctx.Values.httpClient.connection.proxyHost }}
- name: HTTP_CLIENT_PROXY_HOST
  value: {{ .ctx.Values.httpClient.connection.proxyHost | quote }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxyPort }}
- name: HTTP_CLIENT_PROXY_PORT
  value: {{ .ctx.Values.httpClient.connection.proxyPort | quote }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxySslCaBundlePath }}
- name: HTTP_CLIENT_PROXY_SSL_CA_BUNDLE_PATH
  value: {{ .ctx.Values.httpClient.connection.proxySslCaBundlePath | quote }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxyUsername }}
{{ include "base.valueSource.env" (dict "name" "HTTP_CLIENT_PROXY_USERNAME" "src" .ctx.Values.httpClient.connection.proxyUsername "ctx" .ctx) }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxyPassword }}
{{ include "base.valueSource.env" (dict "name" "HTTP_CLIENT_PROXY_PASSWORD" "src" .ctx.Values.httpClient.connection.proxyPassword "ctx" .ctx) }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxySslCertPath }}
- name: HTTP_CLIENT_PROXY_SSL_CERT_PATH
  value: {{ .ctx.Values.httpClient.connection.proxySslCertPath | quote }}
{{- end }}
{{- if .ctx.Values.httpClient.connection.proxySslKeyPath }}
- name: HTTP_CLIENT_PROXY_SSL_KEY_PATH
  value: {{ .ctx.Values.httpClient.connection.proxySslKeyPath | quote }}
{{- end }}
- name: HTTP_CLIENT_POOL_TIMEOUT_SECONDS
  value: {{ .ctx.Values.httpClient.tuning.poolTimeoutSeconds | quote }}
- name: HTTP_CLIENT_MAX_CONNECTIONS
  value: {{ .ctx.Values.httpClient.tuning.maxConnections | quote }}
- name: HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS
  value: {{ .ctx.Values.httpClient.tuning.maxKeepaliveConnections | quote }}
- name: URL_SAFETY_ENABLED
  value: {{ .ctx.Values.urlSafety.enabled | quote }}
- name: URL_SAFETY_RESOLVE_REDIRECTS
  value: {{ .ctx.Values.urlSafety.redirects.resolveRedirects | quote }}
- name: URL_SAFETY_ALLOWED_SCHEMES
  value: {{ .ctx.Values.urlSafety.network.allowedSchemes | toJson | quote }}
- name: URL_SAFETY_LOCALHOST_HOSTS
  value: {{ .ctx.Values.urlSafety.network.localhostHosts | toJson | quote }}
- name: URL_SAFETY_METADATA_HOSTS
  value: {{ .ctx.Values.urlSafety.network.metadataHosts | toJson | quote }}
- name: URL_SAFETY_CLUSTER_LOCAL_SUFFIX
  value: {{ .ctx.Values.urlSafety.network.clusterLocalSuffix | quote }}
- name: URL_SAFETY_SERVICE_SUFFIX
  value: {{ .ctx.Values.urlSafety.network.serviceSuffix | quote }}
- name: URL_SAFETY_MAX_REDIRECT_HOPS
  value: {{ .ctx.Values.urlSafety.redirects.maxRedirectHops | quote }}
- name: URL_SAFETY_REDIRECT_TIMEOUT_SECONDS
  value: {{ .ctx.Values.urlSafety.redirects.redirectTimeoutSeconds | quote }}
{{- end -}}

{{- define "base.externalService.networkPolicy.cilium.egress.rules.ext" -}}
{{ if and .Values.googleSearch .Values.googleSearch.enabled }}
{{- $endpoint := required "googleSearch.connection.apiEndpoint is required when googleSearch.enabled is true. Set it in your environment overlay." .Values.googleSearch.connection.apiEndpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostParts := $parsed.host | splitList ":" -}}
{{- $host := first $hostParts -}}
{{- $port := "443" -}}
{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}
{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}
- toFQDNs:
  - matchName: {{ $host | quote }}
  toPorts:
  - ports:
    - port: {{ $port | quote }}
      protocol: TCP
{{- end }}
{{ if and .Values.braveSearch .Values.braveSearch.enabled }}
{{- $endpoint := required "braveSearch.connection.apiEndpoint is required when braveSearch.enabled is true. Set it in your environment overlay." .Values.braveSearch.connection.apiEndpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostParts := $parsed.host | splitList ":" -}}
{{- $host := first $hostParts -}}
{{- $port := "443" -}}
{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}
{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}
- toFQDNs:
  - matchName: {{ $host | quote }}
  toPorts:
  - ports:
    - port: {{ $port | quote }}
      protocol: TCP
{{- end }}
{{ if and .Values.perplexitySearch .Values.perplexitySearch.enabled }}
{{- $endpoint := required "perplexitySearch.connection.apiEndpoint is required when perplexitySearch.enabled is true. Set it in your environment overlay." .Values.perplexitySearch.connection.apiEndpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostParts := $parsed.host | splitList ":" -}}
{{- $host := first $hostParts -}}
{{- $port := "443" -}}
{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}
{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}
- toFQDNs:
  - matchName: {{ $host | quote }}
  toPorts:
  - ports:
    - port: {{ $port | quote }}
      protocol: TCP
{{- end }}
{{ if and .Values.tavily .Values.tavily.enabled }}
{{- $endpoint := required "tavily.connection.apiEndpoint is required when tavily.enabled is true. Set it in your environment overlay." .Values.tavily.connection.apiEndpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostParts := $parsed.host | splitList ":" -}}
{{- $host := first $hostParts -}}
{{- $port := "443" -}}
{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}
{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}
- toFQDNs:
  - matchName: {{ $host | quote }}
  toPorts:
  - ports:
    - port: {{ $port | quote }}
      protocol: TCP
{{- end }}
{{ if and .Values.jina .Values.jina.enabled }}
{{- $domain := required "jina.connection.apiDomain is required when jina.enabled is true. Set it in your environment overlay." .Values.jina.connection.apiDomain -}}
- toFQDNs:
  - matchPattern: {{ printf "*.%s" $domain | quote }}
  toPorts:
  - ports:
    - port: "443"
      protocol: TCP
{{- end }}
{{ if and .Values.firecrawl .Values.firecrawl.enabled }}
{{- $endpoint := required "firecrawl.connection.apiEndpoint is required when firecrawl.enabled is true. Set it in your environment overlay." .Values.firecrawl.connection.apiEndpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostParts := $parsed.host | splitList ":" -}}
{{- $host := first $hostParts -}}
{{- $port := "443" -}}
{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}
{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}
- toFQDNs:
  - matchName: {{ $host | quote }}
  toPorts:
  - ports:
    - port: {{ $port | quote }}
      protocol: TCP
{{- end }}
{{- end -}}

{{- define "base.externalService.networkPolicy.cilium.egress.hasRules.ext" -}}
{{- if or (and .Values.googleSearch .Values.googleSearch.enabled) (and .Values.braveSearch .Values.braveSearch.enabled) (and .Values.perplexitySearch .Values.perplexitySearch.enabled) (and .Values.tavily .Values.tavily.enabled) (and .Values.jina .Values.jina.enabled) (and .Values.firecrawl .Values.firecrawl.enabled) -}}true{{- end -}}
{{- end -}}

{{- define "base.externalService.networkPolicy.kubernetes.egress.validation.ext" -}}
{{- end -}}

{{- define "base.externalService.secretProvider.collectExtByVault.ext" -}}
{{- if and .ctx.Values.googleSearch .ctx.Values.googleSearch.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.googleSearch.connection.apiKey)) }}
{{- end -}}
{{- if and .ctx.Values.braveSearch .ctx.Values.braveSearch.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.braveSearch.connection.apiKey)) }}
{{- end -}}
{{- if and .ctx.Values.perplexitySearch .ctx.Values.perplexitySearch.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.perplexitySearch.connection.apiKey)) }}
{{- end -}}
{{- if and .ctx.Values.bingAgent .ctx.Values.bingAgent.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.bingAgent.connection.endpoint .ctx.Values.bingAgent.connection.bingResourceConnectionString .ctx.Values.bingAgent.connection.bingAgentModel)) }}
{{- end -}}
{{- if and .ctx.Values.vertexaiAgent .ctx.Values.vertexaiAgent.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.vertexaiAgent.connection.serviceAccountCredentials)) }}
{{- end -}}
{{- if and .ctx.Values.tavily .ctx.Values.tavily.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.tavily.connection.apiKey)) }}
{{- end -}}
{{- if and .ctx.Values.jina .ctx.Values.jina.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.jina.connection.apiKey)) }}
{{- end -}}
{{- if and .ctx.Values.firecrawl .ctx.Values.firecrawl.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.firecrawl.connection.apiKey)) }}
{{- end -}}
{{- if or .ctx.Values.httpClient.connection.proxyUsername .ctx.Values.httpClient.connection.proxyPassword -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault "fields" (list .ctx.Values.httpClient.connection.proxyUsername .ctx.Values.httpClient.connection.proxyPassword)) }}
{{- end -}}
{{- end -}}
