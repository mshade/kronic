{{/*
Expand the name of the chart.
*/}}
{{- define "kronic.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kronic.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kronic.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kronic.labels" -}}
helm.sh/chart: {{ include "kronic.chart" . }}
{{ include "kronic.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kronic.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kronic.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kronic.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kronic.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "kronic.adminPassword" -}}
  {{- if empty .Values.auth.adminPassword }}
{{/*
    User can provide pre-existing secret 
*/}}
    {{- $secretObj := (lookup "v1" "Secret" .Release.Namespace .Values.auth.existingSecretName ) | default dict }}
    {{- $secretData := (get $secretObj "data") | default dict }}
    {{- $adminPass := (get $secretData .Values.auth.existingSecretName ) | default (randAlphaNum 16) }}
    {{- if empty $adminPass }}
      {{- $adminPass := "dry-run" }}
    {{- end }}
    {{- printf "%s" $adminPass }}
  {{- else }}
    {{- $adminPass := .Values.auth.adminPassword }}
    {{- printf "%s" $adminPass }}
  {{- end}}
{{- end }}
