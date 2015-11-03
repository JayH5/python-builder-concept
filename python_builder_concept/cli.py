import click
import docker

from py._path.local import LocalPath

from python_builder_concept.builder import Builder, Workspace
from python_builder_concept.config import load_configs


@click.command()
@click.option('--config', required=True,
              help='The path to the config file for the builder.',
              type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option('--build-file', default='.build.yml',
              help='The name of the build config file in the source')
@click.option('--docker-socket', default='unix://var/run/docker.sock',
              help='The address to the Docker daemon socket')
@click.argument('source_dir',
                type=click.Path(exists=True, file_okay=False,
                                resolve_path=True))
@click.argument('workspace_dir',
                type=click.Path(file_okay=False, resolve_path=True))
def main(config, build_file, docker_socket, source_dir, workspace_dir):
    workspace = Workspace(LocalPath(workspace_dir))
    workspace.create()

    source_path = LocalPath(source_dir)
    configs = load_configs(LocalPath(config), source_path.join(build_file))

    docker_client = docker.Client(base_url=docker_socket)

    builder = Builder(configs, workspace, source_path, docker_client)
    builder.build()
