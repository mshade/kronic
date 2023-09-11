from flask import Flask, request, render_template, redirect
from boltons.iterutils import remap

import yaml

from kron import (
    get_cronjobs,
    get_jobs,
    get_jobs_and_pods,
    get_cronjob,
    get_pods,
    get_pod_logs,
    toggle_cronjob_suspend,
    trigger_cronjob,
    update_cronjob,
    delete_cronjob,
    delete_job,
)

app = Flask(__name__, static_url_path="", static_folder="static")


def _strip_immutable_fields(spec):
    spec.pop("status", None)
    metadata = spec.get("metadata", {})

    metadata.pop("uid", None)
    metadata.pop("resourceVersion", None)

    return spec


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/")
def index():
    cronjobs = get_cronjobs()
    namespaces = {}
    # Count cronjobs per namespace
    for cronjob in cronjobs:
        namespaces[cronjob["namespace"]] = namespaces.get(cronjob["namespace"], 0) + 1

    return render_template("index.html", namespaces=namespaces)


@app.route("/namespaces/<name>")
def view_namespace(name):
    cronjob_names = get_cronjobs(name)
    cronjobs = [
        get_cronjob(namespace=name, cronjob_name=cronjob["name"])
        for cronjob in cronjob_names
    ]
    for cron in cronjobs:
        jobs = get_jobs(namespace=name, cronjob_name=cron["metadata"]["name"])
        cron["jobs"] = jobs
        for job in cron["jobs"]:
            job["pods"] = get_pods(
                cron["metadata"]["namespace"], job["metadata"]["name"]
            )

    return render_template("namespace.html", cronjobs=cronjobs, namespace=name)


@app.route("/namespaces/<namespace>/cronjobs/<cronjob_name>", methods=["GET", "POST"])
def view_cronjob(namespace, cronjob_name):
    if request.method == "POST":
        edited_cronjob = yaml.safe_load(request.form["yaml"])
        cronjob = update_cronjob(namespace, edited_cronjob)
        if cronjob["metadata"]["name"] != cronjob_name:
            return redirect(
                f"/namespaces/{namespace}/cronjobs/{cronjob['metadata']['name']}",
                code=302,
            )
    else:
        cronjob = get_cronjob(namespace, cronjob_name)

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
def api_index():
    # Return all cronjobs
    jobs = get_cronjobs()
    return jobs


@app.route("/api/namespaces/<namespace>/cronjobs")
@app.route("/api/namespaces/<namespace>")
def api_namespace(namespace):
    cronjobs = get_cronjobs(namespace)
    return cronjobs


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>")
def api_get_cronjob(namespace, cronjob_name):
    cronjob = get_cronjob(namespace, cronjob_name)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/clone", methods=["POST"]
)
def api_clone_cronjob(namespace, cronjob_name):
    cronjob_spec = get_cronjob(namespace, cronjob_name)
    new_name = request.json["name"]
    cronjob_spec["metadata"]["name"] = new_name
    cronjob_spec["spec"]["jobTemplate"]["metadata"]["name"] = new_name
    cronjob_spec = _strip_immutable_fields(cronjob_spec)
    print(cronjob_spec)
    cronjob = update_cronjob(namespace, cronjob_spec)
    return cronjob


@app.route("/api/namespaces/<namespace>/cronjobs/create", methods=["POST"])
def api_create_cronjob(namespace):
    cronjob_spec = request.json["data"]
    cronjob = update_cronjob(namespace, cronjob_spec)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/delete", methods=["POST"]
)
def api_delete_cronjob(namespace, cronjob_name):
    deleted = delete_cronjob(namespace, cronjob_name)
    return deleted


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/suspend",
    methods=["GET", "POST"],
)
def api_toggle_cronjob_suspend(namespace, cronjob_name):
    if request.method == "GET":
        """Return the suspended status of the <cronjob_name>"""
        cronjob = get_cronjob(namespace, cronjob_name)
        return cronjob
    if request.method == "POST":
        """Toggle the suspended status of <cronjob_name>"""
        cronjob = toggle_cronjob_suspend(namespace, cronjob_name)
        return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/trigger", methods=["POST"]
)
def api_trigger_cronjob(namespace, cronjob_name):
    """Manually trigger a job from <cronjob_name>"""
    cronjob = trigger_cronjob(namespace, cronjob_name)
    status = 200
    if "error" in cronjob:
        status = cronjob["error"]

    return cronjob, status


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>/getJobs")
def api_get_jobs(namespace, cronjob_name):
    jobs = get_jobs_and_pods(namespace, cronjob_name)
    return jobs


@app.route("/api/namespaces/<namespace>/pods")
def api_get_pods(namespace):
    pods = get_pods(namespace)
    return pods


@app.route("/api/namespaces/<namespace>/pods/<pod_name>/logs")
def api_get_pod_logs(namespace, pod_name):
    logs = get_pod_logs(namespace, pod_name)
    return logs


@app.route("/api/namespaces/<namespace>/jobs/<job_name>/delete", methods=["POST"])
def api_delete_job(namespace, job_name):
    deleted = delete_job(namespace, job_name)
    return deleted
