import click

from py._path.local import LocalPath

from python_builder_concept.builder import Builder, BuildConfig, Workspace


@click.command()
@click.option('--build-file', default='.build.yml',
              help='The name of the build config file in the source')
@click.option('--docker-socket', default='unix://var/run/docker.sock',
              help='The address to the Docker daemon socket')
@click.argument('source_dir',
                type=click.Path(exists=True, file_okay=False,
                                resolve_path=True))
@click.argument('workspace_dir',
                type=click.Path(file_okay=False, resolve_path=True))
def main(build_file, docker_socket, source_dir, workspace_dir):
    workspace = Workspace(LocalPath(workspace_dir))
    workspace.create()

    source_path = LocalPath(source_dir)
    config = BuildConfig.from_yaml_file(source_path.join(build_file))

    builder = Builder(workspace, source_path, config, docker_socket)
    builder.build()
