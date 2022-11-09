from invoke import Collection, task

from amazon_product_search.constants import IMAGE_URI, PROJECT_ID, REGION
from amazon_product_search.timestamp import get_unix_timestamp
from tasks import data_tasks, es_tasks, synonyms_tasks


@task
def format(c):
    """Run formatters (isort and black)."""
    print("Running isort...")
    c.run("poetry run isort .")

    print("Running black...")
    c.run("poetry run black .")
    print("Done")


@task
def lint(c):
    """Run linters (isort, black, flake8, and mypy)."""
    print("Running isort...")
    c.run("poetry run isort . --check")

    print("Running black...")
    c.run("poetry run black . --check")

    print("Running flake8...")
    c.run("poetry run pflake8 src tests tasks")

    print("Running mypy...")
    c.run("poetry run mypy src")
    print("Done")


@task
def demo(c):
    c.run("poetry run streamlit run src/demo/🏠_Home.py")


@task
def build_on_cloud(c):
    command = f"""
    gcloud builds submit . \
        --config=cloudbuild.yaml \
        --substitutions=_IMAGE={IMAGE_URI} \
        --timeout=60m
    """
    c.run(command)


@task
def hello_on_cloud(c):
    now = get_unix_timestamp()
    display_name = f"hello-{now}"

    command = f"""
    gcloud ai custom-jobs create \
        --region={REGION} \
        --display-name={display_name} \
        --config=vertexai/hello.yaml
    """
    c.run(command)
    c.run(f"open https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={PROJECT_ID}")


ns = Collection()
ns.add_task(format)
ns.add_task(lint)
ns.add_task(demo)
ns.add_task(build_on_cloud)
ns.add_task(hello_on_cloud)
ns.add_collection(Collection.from_module(data_tasks, name="data"))
ns.add_collection(Collection.from_module(es_tasks, name="es"))
ns.add_collection(Collection.from_module(synonyms_tasks, name="synonyms"))
