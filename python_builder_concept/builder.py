from __future__ import print_function, unicode_literals
from datetime import datetime
from pkg_resources import find_distributions

import json
import sys

import docker
import pystache
import yaml


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


class BuildConfig(object):
    def __init__(self, buildscript, postinstall, build_dependencies,
                 runtime_dependencies):
        self.buildscript = buildscript
        self.postinstall = postinstall
        self.build_dependencies = build_dependencies
        self.runtime_dependencies = runtime_dependencies

    @classmethod
    def from_yaml_file(self, path):
        with path.open() as yaml_file:
            yaml_content = yaml.load(yaml_file)

        deps = yaml_content.get('dependencies')
        if deps is not None:
            build_deps = deps.get('build')
            runtime_deps = deps.get('runtime')

        return BuildConfig(
            yaml_content.get('buildscript'),
            yaml_content.get('postinstall'),
            build_deps,
            runtime_deps
        )


class Builder(object):

    def __init__(self, workspace, source_path, config, docker_socket):
        self.workspace = workspace
        self.source_path = source_path
        self.config = config
        self.docker_client = docker.Client(base_url=docker_socket)

    def build(self):
        self.copy_source()
        self.write_builder_dockerfile()
        self.build_builder_image()
        self.run_builder_container()

    def copy_source(self):
        print('Copying source to workspace...')
        self.source_path.copy(self.workspace.source_path)

    def write_builder_dockerfile(self):
        print('Writing builder dockerfile...')
        content = self.generate_builder_dockerfile()
        path = self.workspace.path.join('builder.dockerfile')
        path.write(content)

    def generate_builder_dockerfile(self):
        with open('templates/builder.dockerfile.mustache') as template_file:
            template = template_file.read()

        data = {
            'base_image': 'base-cpython-ubuntu',
            'has_dependencies?': bool(self.config.build_dependencies),
            'dependencies': [{'package': dep} for dep in
                             sorted(self.config.build_dependencies)]
        }
        if self.config.buildscript:
            data['buildscript?'] = {'path': self.config.buildscript}
        return pystache.render(template, data)

    def builder_image_tag(self):
        dist = get_project_distribution(str(self.workspace.source_path))
        return '%s-builder:%s' % (dist.project_name, dist.version)

    def build_builder_image(self):
        print('Building builder image...')
        response = self.docker_client.build(
            tag=self.builder_image_tag(),
            path=str(self.workspace.path),
            rm=True,
            pull=False,
            dockerfile='builder.dockerfile')
        log_docker_json_stream(response)

    def builder_container_name(self):
        dist = get_project_distribution(str(self.workspace.source_path))
        return '%s-build-%s' % (
            dist.project_name, datetime.utcnow().strftime('%Y-%m-%dT%H-%M'))

    def run_builder_container(self):
        print('Running builder container...')
        # Create the container...
        host_config = self.docker_client.create_host_config(binds=[
            '%s:/build' % (self.workspace.build_path,)
        ])
        container = self.docker_client.create_container(
            image=self.builder_image_tag(),
            name=self.builder_container_name(),
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
