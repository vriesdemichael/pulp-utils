import io
import json
import os
from contextlib import redirect_stdout, redirect_stderr
from enum import Enum
from subprocess import check_output as check_output_raw

from tqdm import tqdm


VERBOSE = True


def proper_clear():
    # Load apps
    import django
    django.setup()

    # Load resources (can only be done after app)
    from pulpcore.app.models import ContentArtifact, Content, ScanResult

    deleted_ca, deleted_ca_row_counts = ContentArtifact.objects.all().delete()
    deleted_content, deleted_content_row_counts = Content.objects.all().delete()
    deleted_sr, deleted_sr_row_counts = ScanResult.objects.all().delete()
    print(f"Deleted: {deleted_ca} {deleted_content} {deleted_sr}")

def check_output(*args, **kwargs):
    cmd = args[0]
    env = os.environ.copy()
    env["PATH"] = f"/opt/pulp/bin:{env['PATH']}"
    f = io.StringIO()
    with redirect_stdout(f):
        with redirect_stderr(f):
            cmd_output = check_output_raw(["bash", "-c", cmd], env=env, encoding="utf-8")
    stdout_output = f.getvalue()

    if VERBOSE:
        if cmd_output:
            tqdm.write("Command output")
            tqdm.write(cmd_output)
        if stdout_output:
            tqdm.write("STDOUT output")
            tqdm.write(stdout_output)
    return cmd_output


class Policy(Enum):
    ON_DEMAND = "on_demand"
    STREAMED = "streamed"
    IMMEDIATE = "immediate"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


def create_repo(*args, **kwargs):
    create_repo_cmd = f"pulp python repository create --name { kwargs['name'] }"
    return check_output(create_repo_cmd), kwargs


def create_remote(*args, **kwargs):
    packages_json = json.dumps(kwargs['packages'])

    create_remote_cmd = f"pulp python remote create --name {kwargs['name']} --url https://pypi.org/ --includes '{packages_json}' --policy {kwargs['policy']}"
    return check_output(create_remote_cmd), kwargs


def sync_remote(*args, **kwargs):
    sync_repo_cmd = f"pulp python repository sync --name { kwargs['name'] } --remote { kwargs['name'] }"
    return check_output(sync_repo_cmd), kwargs


def create_publication(*args, **kwargs):
    create_publication_cmd = f"pulp python publication create --repository {kwargs['name']} | jq -r .pulp_href"
    publication_href = check_output(create_publication_cmd).replace("\n", "")
    kwargs['publication_href'] = publication_href
    return publication_href, kwargs


def create_distribution(*args, **kwargs):
    create_distribution_cmd = f"pulp python distribution create --name {kwargs['name']} --base-path {kwargs['name']} --publication {kwargs['publication_href']} "
    return check_output(create_distribution_cmd), kwargs


def workflow_initiate(name: str, policy: Policy, packages):
    kwargs = {"name": name, "policy": policy, "packages": packages}
    # for step in [create_repo, create_remote, sync]

    steps = [
        create_repo,
        create_remote,
        sync_remote,
        create_publication,
        create_distribution,
    ]
    for step in tqdm(steps, leave=False):
        _, kwargs = step(**kwargs)


def destroy_existing():
    tqdm.write("Removing distributions")
    check_output(r"pulp python distribution list | jq -M -r .[].name | xargs -r -d '\n' -n1 -t pulp python distribution destroy --name")
    tqdm.write("Removing publications")
    check_output(r"pulp python publication list | jq -M -r .[].pulp_href | xargs -r -d '\n' -n1 -t pulp python publication destroy --href")
    tqdm.write("Removing repositories")
    check_output(r"pulp python repository list | jq -M -r .[].name | xargs -r -d '\n' -n1 -t pulp python repository destroy --name")
    tqdm.write("Removing remotes")
    check_output(r"pulp python remote list | jq -M -r .[].name | xargs -r -d '\n' -n1 -t pulp python remote destroy --name")
    print(check_output(r"pulp orphans delete"))  # Deletes unconnected content and artifacts


def main():
    destroy_existing()
    proper_clear()

    policy_packages = {
        # Policy.ON_DEMAND: ["scipy", "pyyaml"],
        # Policy.STREAMED: ["pyxdg", "requests"],
        Policy.IMMEDIATE: [
            "ctc",
            # "wasabi ",
            # "plac",
        ]
    }
    for policy, packages in tqdm(policy_packages.items(), desc="Policies"):
        workflow_initiate(name=f"pypi_{policy}", policy=policy, packages=packages)

def test_pipeline():
    import django
    django.setup()

    from pulp_python.app.tasks.sync import PythonBanderStage
    from pulp_python.app.models import PythonRemote
    from pulp_python.app.models import PythonRepository
    from pulpcore.plugin.stages import DeclarativeVersion

    create_remote(name="manual_test", packages=["ctc"], policy=Policy.IMMEDIATE)
    create_repo(name="manual_test")
    try:
        remote = PythonRemote.objects.all()[0]
        repo = PythonRepository.objects.all()[0]


        first_stage = PythonBanderStage(remote)
        stages = DeclarativeVersion(first_stage, repo, True).create()

    except Exception as e:
        destroy_existing()
        raise e


if __name__ == '__main__':
    test_pipeline()
    # main()

