from __future__ import print_function, unicode_literals

import json
import sys

import yaml

import docker


def log_docker_stream(response_stream):
    for entry in response_stream:
        content = json.loads(entry)
        if 'stream' in content:
            sys.stdout.write(content['stream'])
        elif 'error' in content:
            raise RuntimeError(str(content))
        else:
            raise RuntimeError('Unknown response from Docker daemon')


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
    def __init__(self, name, buildscript, postinstall, build_dependencies,
                 runtime_dependencies):
        self.name = name
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
            yaml_content['name'],
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
        self.copy_buildscript()
        self.write_builder_dockerfile()
        self.build_builder_image()
        self.run_builder_container()

    def copy_source(self):
        print('Copying source to workspace...')
        self.source_path.copy(self.workspace.source_path)

    def copy_buildscript(self):
        print('Copying buildscript to workspace...')
        dest = self.workspace.path.join('buildscript.sh')
        if self.config.buildscript is not None:
            src = self.workspace.source_path.join(self.config.buildscript)
            src.copy(dest)
        else:
            pass
            # TODO: fix this with /tmp directories
            # content = self.generate_default_buildscript()
            # dest.write(content)
            # dest.chmod(755)

    def generate_default_buildscript(self):
        return """#!/bin/bash
cd /source
pip wheel .
"""

    def write_builder_dockerfile(self):
        print('Writing builder dockerfile...')
        content = self.generate_builder_dockerfile()
        path = self.workspace.path.join('builder.dockerfile')
        path.write(content)

    def generate_builder_dockerfile(self):
        base_image = 'base-cpython'
        build_deps = ' '.join(sorted(self.config.build_dependencies))
        return """FROM {base_image}

RUN $APT_GET_INSTALL {build_deps}

RUN pip --no-cache-dir install wheel

VOLUME /build
COPY ./source /source
COPY ./buildscript.sh /buildscript.sh

ENV WHEELHOUSE=/build/wheelhouse
ENV PIP_WHEEL_DIR=$WHEELHOUSE
ENV PIP_FIND_LINKS=$WHEELHOUSE

CMD /buildscript.sh
""".format(base_image=base_image, build_deps=build_deps)

    def builder_tag(self):
        return "%s-builder" % (self.config.name)

    def build_builder_image(self):
        print('Building builder image...')
        response = self.docker_client.build(
            tag=self.builder_tag(),
            path=str(self.workspace.path),
            rm=True,
            pull=False,
            dockerfile='builder.dockerfile')
        log_docker_stream(response)

    def run_builder_container(self):
        print('Running builder container...')
        host_config = self.docker_client.create_host_config(binds=[
            '%s:/build' % (self.workspace.build_path,)
        ])
        container = self.docker_client.create_container(
            image=self.builder_tag(),
            host_config=host_config
        )

        self.docker_client.start(container=container.get('Id'))
