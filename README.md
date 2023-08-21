# Kron

Todo:
- show cronjobs and associated jobs + pods
- trigger cronjobs
- show cronjobs in given namespace
- show logs for pod
- events for cron/job/pod

/api/ - list all cronjobs across all namespaces

    /namespaces/ - list all namespaces
    /namespace/<name> - get cronjobs in that namespace
    /namespaces/<name>/pods/<name>
    /namespaces/<name>/pods/<name>/log

    /