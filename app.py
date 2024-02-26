from flask import Flask, request, render_template, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash

from functools import wraps
import yaml

import config
from kron import (
    get_cronjobs,
    get_jobs,
    get_jobs_and_pods,
    get_cronjob,
    get_pods,
    get_pod_logs,
    pod_is_owned_by,
    toggle_cronjob_suspend,
    trigger_cronjob,
    update_cronjob,
    delete_cronjob,
    delete_job,
)

app = Flask(__name__, static_url_path="", static_folder="static")
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    # No users defined, so no auth enabled
    if not config.USERS:
        return True
    else:
        if username in config.USERS and check_password_hash(
            config.USERS.get(username), password
        ):
            return username


# A namespace filter decorator
def namespace_filter(func):
    @wraps(func)
    def wrapper(namespace, *args, **kwargs):
        if config.ALLOW_NAMESPACES:
            if namespace in config.ALLOW_NAMESPACES.split(","):
                return func(namespace, *args, **kwargs)
        else:
            return func(namespace, *args, **kwargs)

        data = {
            "error": f"Request to {namespace} denied due to KRONIC_ALLOW_NAMESPACES setting",
            "namespace": namespace,
        }
        if request.headers.get(
            "content-type", None
        ) == "application/json" or request.base_url.startswith("/api/"):
            return data, 403
        else:
            return render_template("denied.html", data=data)

    return wrapper


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
@app.route("/namespaces/")
@auth.login_required
def index():
    if config.NAMESPACE_ONLY:
        return redirect(
            f"/namespaces/{config.KRONIC_NAMESPACE}",
            code=302,
        )

    cronjobs = get_cronjobs()
    namespaces = {}
    # Count cronjobs per namespace
    for cronjob in cronjobs:
        namespaces[cronjob["namespace"]] = namespaces.get(cronjob["namespace"], 0) + 1

    return render_template("index.html", namespaces=namespaces)


@app.route("/namespaces/<namespace>")
@namespace_filter
@auth.login_required
def view_namespace(namespace):
    cronjobs = get_cronjobs(namespace)
    cronjobs_with_details = []
    all_pods = get_pods(namespace=namespace)

    for cronjob in cronjobs:
        cronjob_detail = get_cronjob(namespace, cronjob["name"])
        jobs = get_jobs(namespace=namespace, cronjob_name=cronjob["name"])
        for job in jobs:
            job["pods"] = [pod for pod in all_pods if pod_is_owned_by(pod, job["metadata"]["name"])]
        cronjob_detail["jobs"] = jobs
        cronjobs_with_details.append(cronjob_detail)

    return render_template(
        "namespace.html", cronjobs=cronjobs_with_details, namespace=namespace
    )


@app.route("/namespaces/<namespace>/cronjobs/<cronjob_name>", methods=["GET", "POST"])
@namespace_filter
@auth.login_required
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
            "spec": {
                "schedule": "*/10 * * * *",
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "example",
                                        "image": "busybox:latest",
                                        "imagePullPolicy": "IfNotPresent",
                                        "command": [
                                            "/bin/sh",
                                            "-c",
                                            "echo hello; date",
                                        ],
                                    }
                                ],
                                "restartPolicy": "OnFailure",
                            }
                        }
                    }
                },
            },
        }

    cronjob_yaml = yaml.dump(cronjob)
    return render_template("cronjob.html", cronjob=cronjob, yaml=cronjob_yaml)


@app.route("/api/")
@auth.login_required
def api_index():
    if config.NAMESPACE_ONLY:
        return redirect(
            f"/api/namespaces/{config.KRONIC_NAMESPACE}",
            code=302,
        )
    # Return all cronjobs
    jobs = get_cronjobs()
    return jobs


@app.route("/api/namespaces/<namespace>/cronjobs")
@app.route("/api/namespaces/<namespace>")
@namespace_filter
@auth.login_required
def api_namespace(namespace):
    cronjobs = get_cronjobs(namespace)
    return cronjobs


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>")
@namespace_filter
@auth.login_required
def api_get_cronjob(namespace, cronjob_name):
    cronjob = get_cronjob(namespace, cronjob_name)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/clone", methods=["POST"]
)
@namespace_filter
@auth.login_required
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
@namespace_filter
@auth.login_required
def api_create_cronjob(namespace):
    cronjob_spec = request.json["data"]
    cronjob = update_cronjob(namespace, cronjob_spec)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/delete", methods=["POST"]
)
@namespace_filter
@auth.login_required
def api_delete_cronjob(namespace, cronjob_name):
    deleted = delete_cronjob(namespace, cronjob_name)
    return deleted


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/suspend",
    methods=["GET", "POST"],
)
@namespace_filter
@auth.login_required
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
@namespace_filter
@auth.login_required
def api_trigger_cronjob(namespace, cronjob_name):
    """Manually trigger a job from <cronjob_name>"""
    cronjob = trigger_cronjob(namespace, cronjob_name)
    status = 200
    if "error" in cronjob:
        status = cronjob["error"]

    return cronjob, status


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>/getJobs")
@namespace_filter
@auth.login_required
def api_get_jobs(namespace, cronjob_name):
    jobs = get_jobs_and_pods(namespace, cronjob_name)
    return jobs


@app.route("/api/namespaces/<namespace>/pods")
@namespace_filter
@auth.login_required
def api_get_pods(namespace):
    pods = get_pods(namespace)
    return pods


@app.route("/api/namespaces/<namespace>/pods/<pod_name>/logs")
@namespace_filter
@auth.login_required
def api_get_pod_logs(namespace, pod_name):
    logs = get_pod_logs(namespace, pod_name)
    return logs


@app.route("/api/namespaces/<namespace>/jobs/<job_name>/delete", methods=["POST"])
@namespace_filter
@auth.login_required
def api_delete_job(namespace, job_name):
    deleted = delete_job(namespace, job_name)
    return deleted
