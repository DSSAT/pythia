# Pythia - Release Guide

## Versioning

When it comes to managing software releases for Pythia, understanding how to properly version each release is crucial. Pythia follows the principles of [semantic versioning](https://semver.org/), a widely adopted system designed to give meaning to version numbers. In semantic versioning, a version number is made up of three parts: ``MAJOR.MINOR.PATCH``, with each part serving a specific purpose:

 - **MAJOR** version when you make incompatible API changes,
 - **MINOR** version when you add functionality in a backwards compatible manner, and
 - **PATCH** version when you make backwards compatible bug fixes.

This system helps developers and users understand the scope and impact of each release. Here's a breakdown of when to increment each part of the version number:

 - Increment the **MAJOR** version when there are significant changes that break backward compatibility with the previous versions. This could include changes to the software's architecture, removal of functionalities, or any other changes that would require users to make modifications to their existing setups.
 - Increment the **MINOR** version when new features or functionalities are added in a backward-compatible manner. This means that the new version adds value to the software without disrupting the existing functionalities or forcing changes in the users' setups.
 - Increment the **PATCH** version for minor changes that fix bugs without adding new features or changing existing ones. These should not affect the software's functionality beyond the specific fixes.

## Release Process
Pythia is released through GitHub Actions. Once a release is triggered, the CI/CD pipeline will automatically build the software and publish a Docker image to Dockerhub. A GitHub release is also created.

In order to deploy new versions of Pythia, go to "([Actions > Release](https://github.com/DSSAT/pythia/actions/workflows/release.yml) > Run Workflow > fill in the version number, follow [versioning](#versioning) to figure out this information > Run workflow).

![image](https://github.com/DSSAT/pythia/assets/18128642/a5db0435-9d17-4be8-82c8-54adcbcf860d)

> **IMPORTANT:** The version number must strictly match what is described in [versioning](#versioning). **Do not** add any kind of prefix or suffix that is not semantically valid.
 
> **IMPORTANT:** The version number on ``pyproject.toml`` is automatically updated by the CI/CD pipeline. **Do not** change it manually.
