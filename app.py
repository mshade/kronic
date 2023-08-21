from flask import Flask, request

from kron import getCronJobs, getNamespaces, getJobs, getCronJob, getPods, getPodLogs, toggleCronJob

app = Flask(__name__)

@app.route("/api/")
def index():
    jobs = getCronJobs()
    return jobs

@app.route("/api/namespaces/")
def namespaces():
    namespaces = getNamespaces()
    return namespaces

@app.route("/api/namespaces/<name>/cronjobs")
@app.route("/api/namespaces/<name>")
def namespace(name):
    jobs = getCronJobs(name)
    return jobs

@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>")
def showCronJob(namespace, cronjob_name):
    cronjob = getCronJob(namespace, cronjob_name)
    return cronjob

@app.route("/api/namespaces/<namespace>/cronjobs/<cronjob_name>/suspend", methods = ['GET', 'POST'])
def getSetSuspended(namespace, cronjob_name):
    if request.method == 'GET':
        """Return the suspended status of the <cronjob_name>"""
        cronjob = getCronJob(namespace, cronjob_name)
        return cronjob
    if request.method == 'POST':
        """Toggle the suspended status of <cronjob_name>"""
        cronjob = toggleCronJob(namespace, cronjob_name)
        return cronjob


@app.route('/api/namespaces/<namespace>/jobs', defaults={'cronjob_name': None})
@app.route('/api/namespaces/<namespace>/jobs/<cronjob_name>')
def showJobs(namespace, cronjob_name):
    jobs = getJobs(namespace, cronjob_name)
    return jobs

@app.route('/api/namespaces/<namespace>/pods')
def showPods(namespace):
    pods = getPods(namespace)
    return pods

@app.route('/api/namespaces/<namespace>/pods/<pod_name>/logs')
def showPodLogs(namespace, pod_name):
    logs = getPodLogs(namespace, pod_name)
    return logs
