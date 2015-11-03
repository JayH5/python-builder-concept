# python-builder-concept
Automated building of Python wheels using Docker to create build environments

**NOTE:** This code is still very experimental. There are NO TESTS.

This project explores new ways to "build" Python packages, for a potential "Sideloader 2.0". It is very focussed on just the build process and so does not work with any git operations at the moment (it simply takes a path to a directory at runtime).

### Docker-build process
#### Project config - `.build.yml`
`python-builder-concept` takes the sideloader's `.deploy.yaml` and cuts away as much as possible. It uses a `.build.yml` that could look like this:
```yaml
deb:
  buildscript: scripts/build.sh
  postinstall: scripts/postinst.sh
  dependencies:
    build:
      - libffi-dev
      - libssl-dev
    runtime:
      - libffi6
      - openssl
rpm:
  buildscript: scripts/build.sh
  postinstall: scripts/postinst.sh
  dependencies:
    build:
      - libffi-devel
      - openssl-devel
    runtime:
      - libffi
      - openssl
```

All the fields are optional. Ideally, the user would not need to write build or postinstall scripts at all. `deb` and `rpm` are what could be called *build flavours*. To build a package the minimum that the `.build.yml` needs to contain is one flavour. So, for very simple projects that only need `.deb` packages the `.build.yml` could just look like:
```yaml
deb:
```

Build flavours are defined in config for `python-builder-concept`...

#### `python-builder-concept` config
Build flavours are completely configured through the config and it should not require any code changes to add new build flavours. Here is an example of a config:
```yaml
deb:
  base_image: base-cpython-ubuntu14.04
  base_dependencies:
      build:
        - build-essential
        - python-dev
      runtime:
        - libffi6
```

* `base_image`: the name of the docker image to use as the base for building (and possibly eventually running) the source
* `base_dependencies`: these packages will be installed for building (`build`) and as package dependencies (`runtime`) on top of whatever is defined in the project's `.build.yml`. This is useful for very common dependencies such as `build-essential` for compiling C code.

#### Base images
A number of dockerfiles for base images are provided in `docker/`. Users can define their own base images. There are a few requirements for a base image.

* It must have a Python installed. (i.e. running the command `python` must run the Python implementation of your choice).
* It must have pip installed. (Must be able to run `pip` and have things installed with `pip install` available in the `PATH`).
* It must have the environment variable `$PKG_INSTALL` defined such that running `$PKG_INSTALL pkg1 pkg2` installs the packages `pkg1` and `pkg2` with the distribution's package manager. (Ideally this command should do things like update and clean up package indexes automatically).

...and that's it. We obviously have to make some basic assumptions about what the base images look like so things that have some crazy filesystem structure may not work.

### How it works
Given:
* A config that defines some build flavours. (`./config.yml`)
* A directory with Python source code in it (with a `setup.py`) and a `.build.yml` file. (`~/ws/my-python-project`)
* A directory to use as a workspace, possibly a temporary directory. (`/tmp/workspace`)

Run:
`builder --config ./config.yml ~/ws/my-python-project /tmp/workspace`

What happens:
* The source directory is copied into the workspace
* For each build flavour in the project's `.build.yml`, if the build flavour is defined in the config...
  * A "builder" dockerfile is generated and placed in the root workspace directory.
  * The builder dockerfile is built into an image. The builder has all the build dependencies installed and the buildscript copied in if one is being used.
  * The builder image is run. It builds all the project dependencies into wheels which are stored at `/tmp/workspace/build/wheelhouse`.
* **TODO**: The wheels are packaged into a package file (e.g. `.deb`). Using `fpm`.
* **TODO**: A runtime docker image is created.
