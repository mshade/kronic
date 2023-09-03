from kubernetes import client, config
from kubernetes.config import ConfigException
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
import logging

log = logging.getLogger("app.kron")

try:
    # Load configuration inside the Pod
    config.load_incluster_config()
except ConfigException:
    # Load configuration from KUBECONFIG
    config.load_kube_config()

# Create the Api clients
v1 = client.CoreV1Api()
batch = client.BatchV1Api()
generic = client.ApiClient()


def _itemFields(response, fields=["name"]):
    """Filter the API object down to only the metadata fields listed"""
    itemFields = []
    for item in response.items:
        x = {}
        for field in fields:
            x[field] = getattr(item.metadata, field)
        itemFields.append(x)

    return itemFields


def _cleanObject(api_object):
    """Convert API object to JSON and strip managedFields"""
    object = generic.sanitize_for_serialization(api_object)
    if "managedFields" in object["metadata"]:
        object["metadata"].pop("managedFields")
    return object


def _getTimeSince(datestring):
    # pod startTime format
    date = datetime.fromisoformat(datestring)
    since = datetime.now(timezone.utc) - date
    d = since.seconds // (3600 * 24)
    h = since.seconds // 3600 % 24
    m = since.seconds % 3600 // 60
    s = since.seconds % 3600 % 60

    if d > 0:
        return f"{d}d {h}h {m}m {s}s"
    elif h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    elif s > 0:
        return f"{s}s"

    return


def _hasLabel(api_object, k, v):
    """Return True if a label is present with specified value"""
    metadata = api_object["metadata"]
    if "labels" in metadata:
        if k in metadata["labels"]:
            if metadata["labels"][k] == v:
                return True
    return False


def getCronJobs(namespace=""):
    if namespace == "":
        cronjobs = batch.list_cron_job_for_all_namespaces()
    else:
        cronjobs = batch.list_namespaced_cron_job(namespace=namespace)

    fields = ["name", "namespace"]
    sorted_cronjobs = sorted(_itemFields(cronjobs, fields), key=lambda x: x["name"])
    return sorted_cronjobs


def getCronJob(namespace, cronjob_name):
    try:
        cronjob = batch.read_namespaced_cron_job(cronjob_name, namespace)
    except ApiException:
        return False

    return _cleanObject(cronjob)


def getNamespaces():
    namespaces = v1.list_namespace()
    return _itemFields(namespaces)


def getJobs(namespace, cronjob_name):
    jobs = batch.list_namespaced_job(namespace=namespace)
    cleaned = [_cleanObject(job) for job in jobs.items]
    filtered = []
    if cronjob_name:
        for job in cleaned:
            if "ownerReferences" in job["metadata"]:
                if job["metadata"]["ownerReferences"][0]["name"] == cronjob_name:
                    filtered.append(job)
            elif _hasLabel(job, "kron.mshade.org/created-from", cronjob_name):
                filtered.append(job)
    else:
        filtered = cleaned

    for job in filtered:
        job["status"]["age"] = _getTimeSince(job["status"]["startTime"])

    return filtered


def getPods(namespace, job_name=None):
    all_pods = v1.list_namespaced_pod(namespace=namespace)
    cleaned = [_cleanObject(pod) for pod in all_pods.items]
    pods = []
    if job_name:
        for pod in cleaned:
            if "ownerReferences" in pod["metadata"]:
                if pod["metadata"]["ownerReferences"][0]["name"] == job_name:
                    pods.append(pod)
    else:
        pods = cleaned

    for pod in pods:
        pod["status"]["age"] = _getTimeSince(pod["status"]["startTime"])

    return pods


def getJobsAndPods(namespace, cronjob_name):
    jobs = getJobs(namespace, cronjob_name)
    for job in jobs:
        job["pods"] = getPods(namespace, job["metadata"]["name"])

    return jobs


def getPodLogs(namespace, pod_name):
    """Return plain text logs for <pod_name> in <namespace>"""
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=1000, timestamps=True
        )
    except ApiException as e:
        if e.status == 404:
            return f"Kronic> Error fetching logs: {e.reason}"
    return logs


def triggerCronJob(namespace, cronjob_name):
    cronjob = batch.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
    job = cronjob.spec.job_template
    date_stamp = datetime.now().strftime("%Y%m%d%H%M%S-%f")
    # Set a unique name that indicates this is a manual invocation
    job.metadata.name = str(job.metadata.name[:16] + "-manual-" + date_stamp)[:63]
    # Set a label to identify jobs created by kron
    job.metadata.labels = {
        "kron.mshade.org/manually-triggered": "true",
        "kron.mshade.org/created-from": cronjob_name,
    }

    try:
        trigger_job = batch.create_namespaced_job(body=job, namespace=namespace)
    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response
    return _cleanObject(trigger_job)


def toggleCronJob(namespace, cronjob_name):
    suspended_status = batch.read_namespaced_cron_job_status(
        name=cronjob_name, namespace=namespace
    )
    patch_body = {"spec": {"suspend": not suspended_status.spec.suspend}}
    cronjob = batch.patch_namespaced_cron_job(
        name=cronjob_name, namespace=namespace, body=patch_body
    )
    return _cleanObject(cronjob)


def updateCronJob(namespace, spec):
    name = spec["metadata"]["name"]
    if getCronJob(namespace, name):
        cronjob = batch.patch_namespaced_cron_job(name, namespace, spec)
    else:
        cronjob = batch.create_namespaced_cron_job(namespace, spec)
    return _cleanObject(cronjob)


def deleteCronJob(namespace, cronjob_name):
    try:
        deleted = batch.delete_namespaced_cron_job(cronjob_name, namespace)
    except ApiException:
        return False
    return _cleanObject(deleted)


def deleteJob(namespace, job_name):
    try:
        deleted = batch.delete_namespaced_job(job_name, namespace)
    except ApiException:
        return False
    return _cleanObject(deleted)
