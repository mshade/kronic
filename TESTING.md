# Integration Testing for Kronic

This document provides instructions for running integration tests with Kronic against a real Kubernetes cluster.

## Prerequisites

- A working Kubernetes cluster (minikube, kind, or a remote cluster)
- Docker installed on your local machine
- kubectl configured to access your cluster

## Setup

1. Ensure your kubeconfig file is readable by the container user:

```bash
chmod +r ~/.kube/config
```

2. Build the Docker image:

```bash
docker build -t kronic .
```

## Running Integration Tests

Run the container with your kubeconfig mounted:

```bash
docker run -i --name kronic --rm \
  -v ~/.kube:/home/kronic/.kube \
  -p 8000:8000 \
  kronic
```

This will:
- Mount your kubeconfig into the container
- Expose the Kronic web interface on port 8000
- Run Kronic with access to your Kubernetes cluster

## Accessing the Web Interface

Once the container is running, you can access the Kronic web interface at:

```
http://localhost:8000
```

## Testing Specific Features

### CronJob Management

1. Navigate to a namespace that contains CronJobs
2. Test viewing CronJob details
3. Test triggering a CronJob manually
4. Test suspending/resuming a CronJob

### Job and Pod Inspection

1. Find a CronJob that has created Jobs
2. Inspect the Job details
3. View the logs of Pods created by the Job

### API Testing

You can test the API endpoints using curl:

```bash
# List all namespaces with CronJobs
curl http://localhost:8000/api/

# List CronJobs in a specific namespace
curl http://localhost:8000/api/namespaces/default

# Get details of a specific CronJob
curl http://localhost:8000/api/namespaces/default/cronjobs/my-cronjob
```

## Troubleshooting

### Permission Issues

If you encounter permission issues with the kubeconfig:

1. Check the permissions on your kubeconfig file:
   ```bash
   ls -la ~/.kube/config
   ```

2. Ensure the file is readable:
   ```bash
   chmod +r ~/.kube/config
   ```

3. If using a non-default kubeconfig location, adjust the mount path accordingly.

### Connection Issues

If Kronic cannot connect to your cluster:

1. Verify your kubeconfig works outside the container:
   ```bash
   kubectl get nodes
   ```

2. Check if the container can resolve the Kubernetes API server hostname:
   ```bash
   docker exec -it kronic nslookup <your-k8s-api-server-host>
   ```

3. For clusters with self-signed certificates, you may need to mount the CA certificate.

## Environment Variables

You can customize Kronic's behavior using environment variables:

```bash
docker run -i --name kronic --rm \
  -v ~/.kube:/home/kronic/.kube \
  -p 8000:8000 \
  -e KRONIC_NAMESPACE=default \
  -e KRONIC_ALLOW_NAMESPACES=default,kube-system \
  kronic
```

Common environment variables:
- `KRONIC_NAMESPACE`: Default namespace to display
- `KRONIC_ALLOW_NAMESPACES`: Comma-separated list of allowed namespaces
- `KRONIC_NAMESPACE_ONLY`: If set to "true", only shows the default namespace