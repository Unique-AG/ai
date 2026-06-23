{{/*
Google Search API extension hooks — search-proxy chart.

Overrides the empty base.externalService.*.ext hooks defined in
charts/base/templates/external-services/_index.tpl with Google-specific logic.

Unlike in-cluster services (Qdrant, PostgreSQL), the Google Custom Search API
is an external internet endpoint. The env hooks use base.valueSource.env for
the sensitive apiKey field. The network policy hooks emit a Cilium toFQDNs rule
derived from connection.apiEndpoint; the Kubernetes NetworkPolicy hook is a
no-op because internet egress is not expressible as a pod-selector-based rule.
*/}}

{{- define "base.externalService.env.ext" -}}
{{- if and .Values.googleSearch .Values.googleSearch.enabled -}}
{{- if not .Values.googleSearch.connection.apiKey -}}
{{- fail "googleSearch.connection.apiKey is required when googleSearch.enabled is true. Set it in your environment overlay." -}}
{{- end -}}
- name: GOOGLE_SEARCH_API_ENDPOINT
  value: {{ required "googleSearch.connection.apiEndpoint is required when googleSearch.enabled is true. Set it in your environment overlay." .Values.googleSearch.connection.apiEndpoint | quote }}
- name: GOOGLE_SEARCH_ENGINE_ID
  value: {{ required "googleSearch.connection.engineId is required when googleSearch.enabled is true. Set it in your environment overlay." .Values.googleSearch.connection.engineId | quote }}
{{ include "base.valueSource.env" (dict "name" "GOOGLE_SEARCH_API_KEY" "src" .Values.googleSearch.connection.apiKey "ctx" .) }}
{{- end -}}
{{- end -}}

{{- define "base.externalService.hooks.env.ext" -}}
{{- if and .ctx.Values.googleSearch .ctx.Values.googleSearch.enabled -}}
{{- if not .ctx.Values.googleSearch.connection.apiKey -}}
{{- fail "googleSearch.connection.apiKey is required when googleSearch.enabled is true. Set it in your environment overlay." -}}
{{- end -}}
- name: GOOGLE_SEARCH_API_ENDPOINT
  value: {{ required "googleSearch.connection.apiEndpoint is required when googleSearch.enabled is true. Set it in your environment overlay." .ctx.Values.googleSearch.connection.apiEndpoint | quote }}
- name: GOOGLE_SEARCH_ENGINE_ID
  value: {{ required "googleSearch.connection.engineId is required when googleSearch.enabled is true. Set it in your environment overlay." .ctx.Values.googleSearch.connection.engineId | quote }}
{{ include "base.valueSource.env" (dict "name" "GOOGLE_SEARCH_API_KEY" "src" .ctx.Values.googleSearch.connection.apiKey "ctx" .ctx) }}
{{- end -}}
{{- end -}}

{{- define "base.externalService.networkPolicy.cilium.egress.rules.ext" -}}
{{- if and .Values.googleSearch .Values.googleSearch.enabled -}}
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
{{- end -}}
{{- end -}}

{{- define "base.externalService.networkPolicy.cilium.egress.hasRules.ext" -}}
{{- if and .Values.googleSearch .Values.googleSearch.enabled -}}true{{- end -}}
{{- end -}}

{{- define "base.externalService.networkPolicy.kubernetes.egress.validation.ext" -}}
{{- end -}}

{{- define "base.externalService.secretProvider.collectExtByVault.ext" -}}
{{- if and .ctx.Values.googleSearch .ctx.Values.googleSearch.enabled -}}
{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault
    "fields" (list .ctx.Values.googleSearch.connection.apiKey)) }}
{{- end -}}
{{- end -}}
