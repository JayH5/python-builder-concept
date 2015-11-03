import yaml


def load_configs(base_config_path, build_config_path):
    base_configs = BaseConfig.from_yaml_file(base_config_path)
    build_configs = BuildConfig.from_yaml_file(build_config_path)

    merged_configs = []
    for package_type, build_config in build_configs.items():
        if package_type not in base_configs:
            print('Warning: package type "%s" not in base configs, '
                  'skipping...' % (package_type,))
            continue

        base_config = base_configs[package_type]
        merged_configs.append(MergedConfig.from_configs_merge(
            package_type, base_config, build_config))
    return merged_configs


class BaseConfig(object):
    def __init__(self, base_image, build_dependencies=[],
                 runtime_dependencies=[]):
        self.base_image = base_image
        self.build_dependencies = build_dependencies
        self.runtime_dependencies = runtime_dependencies

    @classmethod
    def from_yaml_file(cls, path):
        with path.open() as yaml_file:
            yaml_content = yaml.load(yaml_file)

        configs = {}
        for package_type, config in yaml_content.items():
            base_dependencies = config.get('base_dependencies', {})
            configs[package_type] = BaseConfig(
                config['base_image'],
                base_dependencies.get('build', []),
                base_dependencies.get('runtime', [])
            )
        return configs


class BuildConfig(object):
    def __init__(self, build_dependencies=[], runtime_dependencies=[],
                 buildscript=None, postinstall=None):
        self.build_dependencies = build_dependencies
        self.runtime_dependencies = runtime_dependencies
        self.buildscript = buildscript
        self.postinstall = postinstall

    @classmethod
    def from_yaml_file(cls, path):
        with path.open() as yaml_file:
            yaml_content = yaml.load(yaml_file)

        build_configs = {}
        for package_type, config in yaml_content.items():
            dependencies = config.get('dependencies', {})
            build_configs[package_type] = BuildConfig(
                dependencies.get('build', []),
                dependencies.get('runtime', []),
                config.get('buildscript'),
                config.get('postinstall')
            )
        return build_configs


class MergedConfig(object):
    def __init__(self, package_type, base_image, build_dependencies=[],
                 runtime_dependencies=[], buildscript=None, postinstall=None):
        self.package_type = package_type
        self.base_image = base_image
        self.build_dependencies = build_dependencies
        self.runtime_dependencies = runtime_dependencies
        self.buildscript = buildscript
        self.postinstall = postinstall

    @classmethod
    def from_configs_merge(cls, package_type, base_config, build_config):
        return MergedConfig(
            package_type,

            # Base image from base config
            base_config.base_image,

            # Dependencies merged from both configs
            list(set(base_config.build_dependencies +
                     build_config.build_dependencies)),
            list(set(base_config.runtime_dependencies +
                     build_config.runtime_dependencies)),

            # Custom scripts from build config
            build_config.buildscript,
            build_config.postinstall
        )
