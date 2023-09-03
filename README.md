# Kronic

![Kronic Logo](/static/android-chrome-192x192.png)

The simple Kubernetes CronJob admin UI.

Kronic is in early alpha. It may eat your cronjobs, pods, or even your job.

## Screenshots

See CronJobs across namespaces:
![Homepage](/.github/kronic-home.png)

View, suspend, trigger, or delete CrobJobs at a glance:
![Cronjobs in a Namespace](/.github/kronic-namespace.png)

Drill down into details to see the status of jobs and pods:
![Cronjob Detail view](/.github/kronic-detail.png)

Get your hands dirty with the raw YAML to edit or duplicate a CronJob:
![Cronjob Edit view](/.github/kronic-edit.png)

## Purpose

CronJobs are a powerful tool, but I have found that developers and stakeholders often need an easy way to inspect the status of jobs,
trigger them ad-hoc, or create a new one-off job based on existing CronJob definitions.

Kronic aims to be a simple UI to view, suspend, trigger, edit, and delete CronJobs in a Kubernetes cluster.

## Try it Out

Kronic can run in-cluster or locally using `KUBECONFIG` for kubernetes API access.

To run in-cluster, edit and apply [k8s/deploy.yaml](/k8s/deploy.yaml). Adjust the RBAC rules, ingress, and other details as you see fit.

To run locally, you can use `docker compose up` or install the Python dependencies and run natively. The compose file expects a valid kubeconfig at `~/.kube/kronic.yaml`.

## Design

Kronic is a small Flask app built with:
- the kubernetes Python client
- gunicorn
- [AlpineJS](https://alpinejs.dev/)
- [PicoCSS](https://picocss.com/)


## Todo

- [ ] Allow/Deny lists for namespaces
- [ ] YAML/Spec Validation on Edit page
- [ ] Async refreshing of job/pods
- [ ] Error handlig for js apiClient
- [ ] Better logging from Flask app and Kron module
- [ ] More unit tests
- [ ] Integration tests against ephemeral k3d cluster
- [ ] CI/CD pipeline and versioning
- [ ] Helm chart
- [ ] Improve localdev stack with automated k3d cluster provisioning
