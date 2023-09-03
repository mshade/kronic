from kubernetes import client


## Create API Objects for testing
container = client.V1Container(name="test", image="busybox", command=["echo", "hello"])
labels = {"app": "test"}
pod_template = client.V1PodTemplateSpec(
    metadata=client.V1ObjectMeta(labels=labels),
    spec=client.V1PodSpec(restart_policy="Never", containers=[container]),
)

job_spec = client.V1JobSpec(template=pod_template)

job = client.V1Job(
    api_version="batch/v1",
    kind="Job",
    metadata=client.V1ObjectMeta(name="hello1", labels=labels),
    spec=job_spec,
)


def create_cronjob(name):
    cronjob = client.V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=client.V1ObjectMeta(name=name, namespace="test", labels=labels),
        spec=client.V1CronJobSpec(schedule="* * * * *", job_template=job),
    )
    return cronjob


jobs = ["first", "second", "third", "fourth", "fifth"]

cronjobList = client.V1CronJobList(
    api_version="batch/v1", items=[create_cronjob(job) for job in jobs]
)
