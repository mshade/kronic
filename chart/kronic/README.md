# kronic

Kronic - The simple Kubernetes CronJob Admin UI

**Homepage:** <https://github.com/mshade/kronic>

![Version: 0.1.5](https://img.shields.io/badge/Version-0.1.5-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: v0.1.2](https://img.shields.io/badge/AppVersion-v0.1.2-informational?style=flat-square)

Kronic is in early alpha. It may eat your cronjobs, pods, or even your job.
Avoid exposing Kronic to untrusted parties or networks.

By default the Kronic helm chart will provide only a `ClusterIP` service. See the [values.yaml](./chart/kronic/values.yaml) for settings,
most notably the `ingress` section.

## Configuration

Kronic can be limited to a list of namespaces. Specify as a comma separated list in the `KRONIC_ALLOW_NAMESPACES` environment variable.
The helm chart exposes this option. Example: `env.KRONIC_ALLOW_NAMESPACES='qa,test,dev'`

Kronic also supports a namespaced installation. The `KRONIC_NAMESPACE_ONLY`
environment variable will limit Kronic to interacting only with CronJobs, Jobs
and Pods in its own namespace. Enabling this setting in the helm chart values
(`env.KRONIC_NAMESPACE_ONLY="true"`) will prevent the creation of ClusterRole and
ClusterRolebinding, using only a namespaced Role and RoleBinding.

### Authentication

Kronic supports HTTP Basic authentication to the backend. It is enabled by default when installed via the helm chart. If no password is specified, the default username is `kronic` and the password is generated randomly.
A username and password can be set via helm values under `auth.adminUsername` and `auth.adminPassword`, or you may create a Kubernetes secret for the deployment to reference.

To retrieve the randomly generated admin password:
```
kubectl --namespace <namespace> get secret <release-name> -ojsonpath="{.data.password}" | base64 -d
```

To create an admin password secret for use with Kronic:
```
kubectl --namespace <namespace> create secret generic custom-password --from-literal=password=<password>

## Tell the helm chart to use this secret:
helm --namespace <namespace> upgrade kronic kronic/kronic --set auth.existingSecretName=custom-password
```

## Installation

A helm chart is available at [./chart/kronic](./chart/kronic/).
By default the Kronic helm chart will provide only a `ClusterIP` service. See the [values.yaml](./chart/kronic/values.yaml) for settings,
most notably the `ingress` section.

> **Warning**
> Avoid exposing Kronic publicly! The default configuration allows for basic authentication, but
> provides only minimal protection.

To install Kronic as `kronic` in its own namespace:

```
helm repo add kronic https://mshade.github.io/kronic/
helm repo update

# Optionally fetch, then customize values file
helm show values kronic/kronic > myvalues.yaml

helm install -n kronic --create-namespace kronic kronic/kronic

# See the NOTES output for accessing Kronic and retrieving the initial admin password
```

If no ingress is configured (see warning above!), expose Kronic via `kubectl port-forward` and access `localhost:8000` in your browser:

```
kubectl -n kronic port-forward deployment/kronic 8000:8000
```

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` | Provide scheduling affinity selectors |
| auth.adminPassword | string | `""` | Specify a password via chart value. Otherwise, randomly generated on first deploy. |
| auth.adminUsername | string | `"kronic"` | Set the username for auth |
| auth.enabled | bool | `true` | Enable backend basic auth |
| auth.existingSecretName | string | `""` | Provide the name of a pre-existing secret containing a data.password: xxx |
| env.KRONIC_ALLOW_NAMESPACES | string | `""` | Comma separated list of namespaces to allow access to, eg: "staging,qa,example" |
| env.KRONIC_NAMESPACE_ONLY | string | `""` | Limit Kronic to its own namespace. Set to "true" to enable. |
| image.pullPolicy | string | `"IfNotPresent"` |  |
| image.repository | string | `"ghcr.io/mshade/kronic"` |  |
| image.tag | string | `""` |  |
| ingress.annotations | object | `{}` | Additional annotations for ingress. Use to configure more advanced auth or controllers other than ingress-nginx |
| ingress.className | string | `""` | The ingressClassName to use for Kronic. Avoid exposing publicly! |
| ingress.enabled | bool | `false` | Expose Kronic via Ingress |
| ingress.hosts | list | `[{"host":"kronic-example.local","paths":[{"path":"/","pathType":"ImplementationSpecific"}]}]` | the ingress hostname(s) for Kronic |
| ingress.tls | list | `[]` |  |
| nodeSelector | object | `{}` |  |
| podAnnotations | object | `{}` |  |
| podSecurityContext | object | `{}` |  |
| rbac.enabled | bool | `true` | Create ClusterRole, ClusterRoleBindings, Role, RoleBindings for cronjob/job/pod permissions. |
| replicaCount | int | `1` | Number of replicas in deployment - min 2 for HA |
| resources.limits.cpu | int | `1` |  |
| resources.limits.memory | string | `"1024Mi"` |  |
| resources.requests.cpu | string | `"10m"` |  |
| resources.requests.memory | string | `"256Mi"` |  |
| securityContext | object | `{}` |  |
| service.port | int | `80` |  |
| service.type | string | `"ClusterIP"` |  |
| serviceAccount.annotations | object | `{}` |  |
| serviceAccount.create | bool | `true` |  |
| tolerations | list | `[]` |  |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.11.0](https://github.com/norwoodj/helm-docs/releases/v1.11.0)
