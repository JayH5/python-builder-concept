from __future__ import print_function, unicode_literals
from datetime import datetime
from pkg_resources import find_distributions

import json
import sys

import pystache


def log_docker_json_stream(response_stream):
    for entry in response_stream:
        content = json.loads(entry)
        if 'stream' in content:
            sys.stdout.write(content['stream'])
        elif 'error' in content:
            raise RuntimeError(str(content))
        else:
            raise RuntimeError('Unknown response from Docker daemon')


def log_docker_stream(response_stream):
    for entry in response_stream:
        sys.stdout.write(entry)


def get_project_distribution(project_path):
    dists = list(find_distributions(project_path))
    if not dists:
        raise RuntimeError('No distributions could be found at %s' % (
            project_path))
    if len(dists) > 1:
        raise RuntimeError('Multiple distributions found at %s' % (
            project_path))

    return dists[0]


class Workspace(object):
    def __init__(self, path):
        self.path = path
        self.source_path = path.join('source')
        self.build_path = path.join('build')

    def prepare(self, source_path):
        self.create()
        self.copy_source(source_path)

    def create(self):
        if not self.path.check():
            self.path.ensure(dir=True)
            self.build_path.mkdir()

    def copy_source(self, source_path):
        print('Copying source to workspace...')
        source_path.copy(self.source_path)

    def get_path(self, *paths):
        return self.path.join(*paths)

    def get_source_path(self, *paths):
        return self.source_path.join(*paths)


class Builder(object):

    def __init__(self, configs, workspace, docker_client):
        self.configs = configs
        self.workspace = workspace
        self.docker_client = docker_client

    def build(self):
        for config in self.configs:
            package_type = config.package_type
            print('Building package type "%s"' % package_type)

            # Generate/write the dockerfile
            dockerfile_filename = self.builder_dockerfile_filename(
                package_type)
            self.write_builder_dockerfile(dockerfile_filename, config)

            # Build the Docker image
            distribution = get_project_distribution(
                str(self.workspace.source_path))
            tag = self.builder_image_tag(distribution, package_type)
            self.build_builder_image(dockerfile_filename, tag)

            # Run the Docker container
            name = self.builder_container_name(distribution, package_type)
            self.run_builder_container(tag, name)

    def builder_dockerfile_filename(self, package_type):
        return '%s-builder.dockerfile' % (package_type)

    def builder_image_tag(self, distribution, package_type):
        return '%s-%s-builder:%s' % (
            distribution.project_name, package_type, distribution.version)

    def builder_container_name(self, distribution, package_type):
        return '%s-%s-build-%s' % (
            distribution.project_name, package_type,
            datetime.utcnow().strftime('%Y-%m-%dT%H-%M'))

    def write_builder_dockerfile(self, filename, config):
        print('Writing builder dockerfile...')
        content = self.generate_builder_dockerfile(config)
        path = self.workspace.get_path(filename)
        path.write(content)

    def generate_builder_dockerfile(self, config):
        with open('templates/builder.dockerfile.mustache') as template_file:
            template = template_file.read()

        data = {
            'base_image': config.base_image,
            'dependencies?': {},
            'buildscript?': {}
        }
        if config.build_dependencies:
            data['dependencies?']['packages'] = [
                {'package': package}
                for package in sorted(config.build_dependencies)
            ]
        if config.buildscript is not None:
            data['buildscript?']['path'] = config.buildscript
        return pystache.render(template, data)

    def build_builder_image(self, dockerfile, tag):
        print('Building builder image...')
        response = self.docker_client.build(
            dockerfile=dockerfile,
            path=str(self.workspace.path),
            tag=tag,
            rm=True,
            pull=False,
        )
        log_docker_json_stream(response)

    def run_builder_container(self, image, name):
        print('Running builder container...')
        # Create the container...
        host_config = self.docker_client.create_host_config(binds={
            str(self.workspace.build_path): {
                'bind': '/build',
                'mode': 'rw',
            }
        })
        container = self.docker_client.create_container(
            image=image,
            name=name,
            host_config=host_config
        )

        # Start it...
        container_id = container['Id']
        self.docker_client.start(container=container_id)
        response = self.docker_client.attach(container=container_id,
                                             logs=True, stream=True)
        log_docker_stream(response)

        # Clean it up...
        self.docker_client.remove_container(container=container_id,
                                            v=True)
