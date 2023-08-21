from kubernetes import client, config
from kubernetes.config import ConfigException
import datetime

try:
    # Load configuration inside the Pod
    config.load_incluster_config()
except ConfigException:
    # Load configuration for testing
    config.load_kube_config()

# Create the Apis
v1 = client.CoreV1Api()
batch = client.BatchV1Api()
generic = client.ApiClient()

def _itemFields(response, fields=["name"]):
    itemFields = []
    for item in response.items:
        x = {}
        for field in fields:
            x[field] = getattr(item.metadata, field)
        itemFields.append(x)

    return itemFields

def _cleanObject(api_object):
    ### Return JSON without managedFields blob
    object = generic.sanitize_for_serialization(api_object)
    object["metadata"].pop("managedFields")
    return object

def getCronJobs(namespace=""):
    if namespace == "":
        cronjobs = batch.list_cron_job_for_all_namespaces()
    else:
        cronjobs = batch.list_namespaced_cron_job(namespace=namespace)
    
    fields = ["name", "namespace"]
    return _itemFields(cronjobs, fields)

def getCronJob(namespace, cronjob_name):
    cronjob = batch.read_namespaced_cron_job(cronjob_name, namespace)
    return _cleanObject(cronjob)

def getNamespaces():
    namespaces = v1.list_namespace()

    return _itemFields(namespaces)

def getJobs(namespace, cronjob_name):
    jobs = batch.list_namespaced_job(namespace=namespace)
    cleaned = [_cleanObject(job) for job in jobs.items]
    if cronjob_name:
        filtered = [job for job in cleaned if job["metadata"]["ownerReferences"][0]["name"] == cronjob_name]
    else:
        filtered = cleaned

    return filtered

def getPods(namespace):
    pods = v1.list_namespaced_pod(namespace=namespace)
    cleaned = [_cleanObject(pod) for pod in pods.items]
    return cleaned

def getPodLogs(namespace, pod_name):
    logs = v1.read_namespaced_pod_log(pod_name, namespace, tail_lines=1000, timestamps=True)
    return logs

def triggerCronJob(namespace, cronjob_name):
    cronjob = batch.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
    job = cronjob.spec.job_template
    date_stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S-%f")
    # Set a unique name that indicates this is a manual invocation
    job.metadata.name = str(job.metadata.name + '-manual-' + date_stamp)[:64]
    # Set a label to identify jobs created by kron
    job.metadata.labels = {"kron.mshade.org/manually-triggered": "true"}

    trigger_job = batch.create_namespaced_job(body=job, namespace=namespace)
    return trigger_job


def toggleCronJob(namespace, cronjob_name):
    suspended_status = batch.read_namespaced_cron_job_status(name=cronjob_name, namespace=namespace)
    patch_body = {
        "spec": {
            "suspend": not suspended_status.spec.suspend
        }
    }
    cronjob = batch.patch_namespaced_cron_job(name=cronjob_name, namespace=namespace, body=patch_body)
    return _cleanObject(cronjob)

