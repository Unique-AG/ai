{{- $hasVulns := false }}
{{- range . }}{{- if .Vulnerabilities }}{{- $hasVulns = true }}{{- end }}{{- end }}
{{- if not $hasVulns }}
✅ No fixable vulnerabilities found, image is clean.
{{- end }}
{{- range . }}
{{- if .Vulnerabilities }}
### {{ .Target }} ({{ .Type }})

{{- range .Vulnerabilities }}{{- if eq .Severity "CRITICAL" }}
- **{{ .Severity }}** — **{{ .PkgName }}** `{{ .InstalledVersion }}` → {{ if .FixedVersion }}`{{ .FixedVersion }}`{{ else }}_unfixed_{{ end }} — [{{ .VulnerabilityID }}]({{ .PrimaryURL }})
{{- end }}{{- end }}
{{- range .Vulnerabilities }}{{- if eq .Severity "HIGH" }}
- **{{ .Severity }}** — **{{ .PkgName }}** `{{ .InstalledVersion }}` → {{ if .FixedVersion }}`{{ .FixedVersion }}`{{ else }}_unfixed_{{ end }} — [{{ .VulnerabilityID }}]({{ .PrimaryURL }})
{{- end }}{{- end }}
{{- range .Vulnerabilities }}{{- if eq .Severity "MEDIUM" }}
- **{{ .Severity }}** — **{{ .PkgName }}** `{{ .InstalledVersion }}` → {{ if .FixedVersion }}`{{ .FixedVersion }}`{{ else }}_unfixed_{{ end }} — [{{ .VulnerabilityID }}]({{ .PrimaryURL }})
{{- end }}{{- end }}

{{- end }}
{{- end }}
