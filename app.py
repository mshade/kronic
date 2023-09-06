from flask import Flask, request, render_template, redirect
from boltons.iterutils import remap

import yaml

from kron import (
    getCronJobs,
    getNamespaces,
    getJobs,
    getJobsAndPods,
    getCronJob,
    getPods,
    getPodLogs,
    toggleCronJob,
    triggerCronJob,
    updateCronJob,
    deleteCronJob,
    deleteJob,
)

app = Flask(__name__, static_url_path="", static_folder="static")


def _strip_immutable_fields(spec):
    try:
        del spec["status"]
    except KeyError:
        pass

    try:
        del spec["metadata"]["uid"]
    except KeyError:
        pass

    try:
        del spec["metadata"]["resourceVersion"]
    except KeyError:
        pass

    return spec


@app.route("/")
def index():
    cronjobs = getCronJobs()
    namespaces = {}
    # Count cronjobs per namespace
    for cronjob in cronjobs:
        namespaces[cronjob["namespace"]] = namespaces.get(cronjob["namespace"], 0) + 1

    return render_template("index.html", namespaces=namespaces)

@app.route("/healthz")
def healthz():
    return {"status": "ok"}

@app.route("/namespaces/<name>")
def namespaceView(name):
    cronjob_names = getCronJobs(name)
    cronjobs = [
        getCronJob(namespace=name, cronjob_name=cronjob["name"])
        for cronjob in cronjob_names
    ]
    for cron in cronjobs:
        jobs = getJobs(namespace=name, cronjob_name=cron["metadata"]["name"])
        cron["jobs"] = jobs
        for job in cron["jobs"]:
            job["pods"] = getPods(
                cron["metadata"]["namespace"], job["metadata"]["name"]
            )

    return render_template("namespace.html", cronjobs=cronjobs, namespace=name)


@app.route("/namespaces/<namespace>/cronjobs/<cronjob_name>", methods=["GET", "POST"])
def cronjobView(namespace, cronjob_name):
    if request.method == "POST":
        edited_cronjob = yaml.safe_load(request.form["yaml"])
        cronjob = updateCronJob(namespace, edited_cronjob)
        if cronjob["metadata"]["name"] != cronjob_name:
            return redirect(
                f"/namespaces/{namespace}/cronjobs/{cronjob['metadata']['name']}",
                code=302,
            )
    else:
        cronjob = getCronJob(namespace, cronjob_name)

    if cronjob:
        cronjob = _strip_immutable_fields(cronjob)
    else:
        cronjob = {
            "apiVersion": "batch/v1",
            "kind": "CronJob",
            "metadata": {"name": cronjob_name, "namespace": namespace},
            "spec": {},
        }

    cronjob_yaml = yaml.dump(cronjob)
    return render_template("cronjob.html", cronjob=cronjob, yaml=cronjob_yaml)


@app.route("/api/")
def apiAllCronJobs():
    jobs = getCronJobs()
    return jobs


@app.route("/api/namespaces/")
def apiNamespaces():
    namespaces = getNamespaces()
    return namespaces


@app.route("/api/namespaces/<namespace>/cronjobs")
@app.route("/api/namespaces/<namespace>")
def apiNamespaceCronjobs(namespace):
    cronjobs = getCronJobs(namespace)
    return cronjobs


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>")
def apiGetCronJob(namespace, cronjob_name):
    cronjob = getCronJob(namespace, cronjob_name)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/clone", methods=["POST"]
)
def apiCloneCronJob(namespace, cronjob_name):
    cronjob_spec = getCronJob(namespace, cronjob_name)
    new_name = request.json["name"]
    cronjob_spec["metadata"]["name"] = new_name
    cronjob_spec["spec"]["jobTemplate"]["metadata"]["name"] = new_name
    cronjob_spec = _strip_immutable_fields(cronjob_spec)
    print(cronjob_spec)
    cronjob = updateCronJob(namespace, cronjob_spec)
    return cronjob


@app.route("/api/namespaces/<namespace>/cronjobs/create", methods=["POST"])
def apiCreateCronJob(namespace):
    cronjob_spec = request.json["data"]
    cronjob = updateCronJob(namespace, cronjob_spec)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/delete", methods=["POST"]
)
def apiDeleteCronJob(namespace, cronjob_name):
    deleted = deleteCronJob(namespace, cronjob_name)
    return deleted


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/suspend",
    methods=["GET", "POST"],
)
def apiToggleSuspended(namespace, cronjob_name):
    if request.method == "GET":
        """Return the suspended status of the <cronjob_name>"""
        cronjob = getCronJob(namespace, cronjob_name)
        return cronjob
    if request.method == "POST":
        """Toggle the suspended status of <cronjob_name>"""
        cronjob = toggleCronJob(namespace, cronjob_name)
        return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/trigger", methods=["POST"]
)
def apiTriggerJob(namespace, cronjob_name):
    """Manually trigger a job from <cronjob_name>"""
    cronjob = triggerCronJob(namespace, cronjob_name)
    status = 200
    if "error" in cronjob:
        status = cronjob["error"]

    return cronjob, status


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>/getJobs")
def apiGetJobs(namespace, cronjob_name):
    jobs = getJobsAndPods(namespace, cronjob_name)
    return jobs


@app.route("/api/namespaces/<namespace>/pods")
def apiGetPods(namespace):
    pods = getPods(namespace)
    return pods


@app.route("/api/namespaces/<namespace>/pods/<pod_name>/logs")
def apiGetPodLogs(namespace, pod_name):
    logs = getPodLogs(namespace, pod_name)
    return logs


@app.route("/api/namespaces/<namespace>/jobs/<job_name>/delete", methods=["POST"])
def apiDeleteJob(namespace, job_name):
    deleted = deleteJob(namespace, job_name)
    return deleted
