import os.path, sys, uuid

from pytest import fixture, mark
from kubernetes import client, config as k8s_config, utils

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app import app
except Exception as e:
    pass


@fixture
def k8s_client():
    k8s_config.load_kube_config()
    return client.ApiClient()


@fixture
def namespace(k8s_client):
    name = str(uuid.uuid4())
    manifest = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": name}}
    utils.create_from_dict(k8s_client, manifest)
    yield name
    corev1 = client.CoreV1Api(k8s_client)
    corev1.delete_namespace(name)


def create_cronjob(k8s_client, namespace):
    name = str(uuid.uuid4())
    manifest = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "schedule": "0 0 * * *",
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "hello",
                                    "image": "busybox:1.28",
                                    "imagePullPolicy": "IfNotPresent",
                                    "command": ["/bin/sh", "-c", "echo Hello"],
                                }
                            ],
                            "restartPolicy": "Never",
                        }
                    }
                }
            },
        },
    }
    utils.create_from_dict(k8s_client, manifest)
    return name


@fixture()
def api():
    app.config.update({"TESTING": True})
    return app.test_client()


@mark.integration
def test_get_cronjob_missing(k8s_client, api, namespace):
    res = api.get(f"/api/namespaces/{namespace}/cronjobs/nonsense")
    assert res.status_code == 404
    assert "nonsense" in res.data.decode("utf-8")


@mark.integration
def test_get_cronjob_succeeds(k8s_client, api, namespace):
    name = create_cronjob(k8s_client, namespace)
    res = api.get(f"/api/namespaces/{namespace}/cronjobs/{name}")
    cronjob = res.json
    assert cronjob["metadata"]["name"] == name
    assert (
        cronjob["spec"]["suspend"] == False
    )  # K8s will have populated this by default


@mark.integration
def test_clone_cronjob_succeeds(k8s_client, api, namespace):
    name = create_cronjob(k8s_client, namespace)
    clone = f"clone-{name}"
    res = api.post(
        f"/api/namespaces/{namespace}/cronjobs/{name}/clone", json={"name": clone}
    )
    cronjob = res.json
    assert res.status_code == 200
    assert cronjob["metadata"]["name"] == clone
