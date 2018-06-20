# MIT License
#
# Copyright (c) 2018 Huddle
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import shutil
import sys

from octopose import nu, octo, subprocess_runner


class LocalDeploy:
    def __init__(self, verbose):
        """LocalDeploy deploys Octopus packages (on the current machine) without needing a tentacle service"""
        self.subprocess_runner = subprocess_runner.SubprocessRunner(verbose)
        self.nu = nu.Nu(self.subprocess_runner)

    def invoke_deploy(self, step_path):
        """invoke_deploy start a deploy for a given powershell script (*Deploy.ps1)"""
        if os.path.exists(step_path):
            print("- {0}".format(step_path))
            if is_64_bit_python_installation():
                args = "powershell.exe {0}".format(step_path)
            else:
                args = "c:\\windows\\sysnative\\cmd.exe /c powershell.exe {0}".format(step_path)
            self.subprocess_runner.run(args, "Running of {0} failed".format(step_path))
        else:
            print("ERROR: Can't find path {0}".format(step_path))

    def deploy(self, data):
        """deploy_local will use the manifest to deploy all packages to the local machine"""
        staging = os.path.normpath(data['StagingLocation'])
        if os.path.exists(staging):
            shutil.rmtree(staging)
        os.makedirs(staging, mode=0o777)

        for key, value in data['Projects'].items():
            project_name = key
            proj_id = octo.get_project_id(project_name)

            if 'Version' not in value:
                latest_release = octo.get_latest_release(proj_id)
                release_version = latest_release['Version']
            else:
                release_version = value['Version']
            print("{0} - {1}".format(project_name, release_version))

            for package in get_package_versions(proj_id, release_version, value['Packages']):
                package_name = package['PackageId']
                version = package['Version']
                print("- NuGet - {0} - {1}".format(package_name, version))
                self.nu.get_deployable(package_name, version, staging)

                self.invoke_deploy("{0}\{1}.{2}\PreDeploy.ps1".format(staging, package_name, version))
                self.invoke_deploy("{0}\{1}.{2}\Deploy.ps1".format(staging, package_name, version))
                self.invoke_deploy("{0}\{1}.{2}\PostDeploy.ps1".format(staging, package_name, version))


def get_package_versions(proj_id, release_version, package_ids_to_deploy):
    release = octo.get_release_for_version(proj_id, release_version)
    step_names_and_version = release['SelectedPackages']
    package_ids_and_step_names = octo.get_specific_packages(release)

    packages_to_deploy = []
    for p in step_names_and_version:
        step_name = p['StepName']
        version = p['Version']

        for pp in package_ids_and_step_names:
            if step_name == pp['StepName']:
                if pp['PackageId'] in package_ids_to_deploy:
                    packages_to_deploy.append({"PackageId": pp['PackageId'], "Version": version})
                break

    return packages_to_deploy


def is_64_bit_python_installation():
    return sys.maxsize > 2**32
