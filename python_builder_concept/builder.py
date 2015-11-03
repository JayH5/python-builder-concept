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

    def create(self):
        if not self.path.check():
            self.path.ensure(dir=True)
            self.build_path.mkdir()


class Builder(object):

    def __init__(self, configs, workspace, source_path, docker_client):
        self.configs = configs
        self.workspace = workspace
        self.source_path = source_path
        self.docker_client = docker_client

    def build(self):
        self.copy_source()
        for config in self.configs:
            print('Building package type "%s"' % config.package_type)
            dockerfile = self.write_builder_dockerfile(config)
            tag = self.builder_image_tag(config.package_type)
            self.build_builder_image(dockerfile, tag)
            name = self.builder_container_name(config.package_type)
            self.run_builder_container(tag, name)

    def copy_source(self):
        print('Copying source to workspace...')
        self.source_path.copy(self.workspace.source_path)

    def write_builder_dockerfile(self, config):
        print('Writing builder dockerfile...')
        content = self.generate_builder_dockerfile(config)
        path = self.workspace.path.join('%s-builder.dockerfile' % (
            config.package_type))
        path.write(content)
        return path

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

    def builder_image_tag(self, package_type):
        dist = get_project_distribution(str(self.workspace.source_path))
        return '%s-%s-builder:%s' % (
            dist.project_name, package_type, dist.version)

    def build_builder_image(self, dockerfile, tag):
        print('Building builder image...')
        response = self.docker_client.build(
            dockerfile=dockerfile.basename,
            path=str(self.workspace.path),
            tag=tag,
            rm=True,
            pull=False,
        )
        log_docker_json_stream(response)

    def builder_container_name(self, package_type):
        dist = get_project_distribution(str(self.workspace.source_path))
        return '%s-%s-build-%s' % (
            dist.project_name, package_type,
            datetime.utcnow().strftime('%Y-%m-%dT%H-%M'))

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
