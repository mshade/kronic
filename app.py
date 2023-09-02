from flask import Flask, request, render_template, redirect
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
)

app = Flask(__name__, static_url_path="", static_folder="static")


@app.route("/")
def index():
    cronjobs = getCronJobs()
    namespaces = {}
    # Count cronjobs per namespace
    for cronjob in cronjobs:
        namespaces[cronjob["namespace"]] = namespaces.get(cronjob["namespace"], 0) + 1

    return render_template("index.html", namespaces=namespaces)


@app.route("/namespaces/<name>")
def namespaces(name):
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

    return render_template("namespaceJobs.html", cronjobs=cronjobs, namespace=name)


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

    del cronjob["status"]
    del cronjob["metadata"]["uid"]
    del cronjob["metadata"]["resourceVersion"]

    cronjob_yaml = yaml.dump(cronjob)
    return render_template("cronjob.html", cronjob=cronjob, yaml=cronjob_yaml)


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/delete", methods=["POST"]
)
def deleteCronJobEndpoint(namespace, cronjob_name):
    deleted = deleteCronJob(namespace, cronjob_name)
    return redirect(f"/namespaces/{namespace}", code=302)


@app.route("/api/")
def allCronJobs():
    jobs = getCronJobs()
    return jobs


@app.route("/api/namespaces/")
def apiNamespaces():
    namespaces = getNamespaces()
    return namespaces


@app.route("/api/namespaces/<namespace>/cronjobs")
@app.route("/api/namespaces/<namespace>")
def namespace(namespace):
    cronjobs = getCronJobs(namespace)
    return cronjobs


@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>")
def showCronJob(namespace, cronjob_name):
    cronjob = getCronJob(namespace, cronjob_name)
    return cronjob


@app.route(
    "/api/namespaces/<namespace>/cronjobs/<cronjob_name>/suspend",
    methods=["GET", "POST"],
)
def getSetSuspended(namespace, cronjob_name):
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
def triggerNewJob(namespace, cronjob_name):
    """Manually trigger a job from <cronjob_name>"""
    cronjob = triggerCronJob(namespace, cronjob_name)
    return cronjob


@app.route("/api/namespaces/<namespace>/jobs", defaults={"cronjob_name": None})
@app.route("/api/namespaces/<namespace>/jobs/<cronjob_name>")
def showJobs(namespace, cronjob_name):
    jobs = getJobsAndPods(namespace, cronjob_name)
    return jobs


@app.route("/api/namespaces/<namespace>/pods")
def showPods(namespace):
    pods = getPods(namespace)
    return pods


@app.route("/api/namespaces/<namespace>/pods/<pod_name>/logs")
def showPodLogs(namespace, pod_name):
    logs = getPodLogs(namespace, pod_name)
    return logs
