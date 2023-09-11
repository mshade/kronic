from kubernetes import client


## Create API Objects for testing

labels = {"app": "test"}


def create_pod_spec(name="test"):
    container = client.V1Container(
        name=name, image="busybox", command=["echo", "hello"]
    )
    pod = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=client.V1PodSpec(restart_policy="Never", containers=[container]),
    )
    return pod


def create_job(name="test"):
    job_spec = client.V1JobSpec(template=create_pod_spec())
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=name, labels=labels),
        spec=job_spec,
    )


def create_cronjob(name="test"):
    cronjob = client.V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=client.V1ObjectMeta(name=name, namespace="test", labels=labels),
        spec=client.V1CronJobSpec(schedule="* * * * *", job_template=create_job()),
    )
    return cronjob


def create_cronjob_list():
    jobs = ["first", "second", "third", "fourth", "fifth"]
    return client.V1CronJobList(
        api_version="batch/v1", items=[create_cronjob(job) for job in jobs]
    )
