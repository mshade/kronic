# Kronic

![Kronic Logo](/static/android-chrome-192x192.png)

![Build / Test](https://github.com/mshade/kronic/actions/workflows/build.yaml/badge.svg)

The simple Kubernetes CronJob admin UI.

Kronic is in early alpha. It may eat your cronjobs, pods, or even your job.


## Screenshots

See CronJobs across namespaces:
![Homepage](/.github/kronic-home.png)

View, suspend, trigger, clone, or delete CrobJobs at a glance:
![Cronjobs in a Namespace](/.github/kronic-namespace.png)

Drill down into details to see the status of jobs and pods:
![Cronjob Detail view](/.github/kronic-detail.png)

Get your hands dirty with the raw YAML to edit a CronJob:
![Cronjob Edit view](/.github/kronic-edit.png)


## Purpose

CronJobs are a powerful tool, but I have found that developers and stakeholders often need an easy way to inspect the status of jobs,
trigger them ad-hoc, or create a new one-off job based on existing CronJob definitions.

Kronic aims to be a simple admin UI / dashboard / manager to view, suspend, trigger, edit, and delete CronJobs in a Kubernetes cluster.


## Deploying to K8S

A helm chart is provided at [./chart/kronic](./chart/kronic/). By default the Kronic helm chart will provide only a `ClusterIP` service. See the [values.yaml](./chart/kronic/values.yaml) for some tweakable settings, most notably `ingress` definition. 

> **Warning**
> Avoid exposing Kronic publicly! The ingress configuration allows for basic authentication, but
> this is only minimal protection. Ensure you change `ingress.auth.password` from the default.
> Best practice would be to use a privately routed ingress class or other network-level protections.
> You may also provide your own basic auth secret using `ingress.auth.secretName`. See [Ingress docs](https://kubernetes.github.io/ingress-nginx/examples/auth/basic/) on creation.

To install Kronic, clone this repository and run:

```
helm install -n kronic --create-namespace kronic ./chart/kronic
```


## Running Locally

Kronic can use a `KUBECONFIG` file to run locally against a cluster. To do so:

```
docker run -i --name kronic \
    -v $HOME/.kube:/home/kronic/.kube \
    -p 8000:8000 \
    ghcr.io/mshade/kronic
```

> **Note**
> You may need to ensure permissions on the kubeconfig file are readable to the `kronic` user (uid 3000). You may also mount a specific kubeconfig file into place, ie: `-v $HOME/.kube/kronic.yaml:/home/kronic/.kube/config`


## Design

Kronic is a small Flask app built with:
- the Python Kubernetes client
- gunicorn
- [AlpineJS](https://alpinejs.dev/)
- [PicoCSS](https://picocss.com/)


## Todo

- [ ] Allow/Deny lists for namespaces
- [ ] Timeline / Cron schedule interpreter or display
- [ ] YAML/Spec Validation on Edit page
- [ ] Async refreshing of job/pods
- [ ] Error handlig for js apiClient
- [ ] Better logging from Flask app and Kron module
- [ ] More unit tests
- [ ] Integration tests against ephemeral k3d cluster
- [ ] CI/CD pipeline and versioning
- [x] Helm chart
- [ ] Improve localdev stack with automated k3d cluster provisioning
