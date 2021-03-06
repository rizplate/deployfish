import json
import requests
import os
import os.path

import boto3


class Terraform(dict):
    """
    This class allows us to retrieve values from our terraform state file.
    """

    def __init__(self, yml):
        self.load_yaml(yml)

    def _get_state_file_from_s3(self, state_file_url):
        s3 = boto3.resource('s3')
        parts = state_file_url[5:].split('/')
        bucket = parts[0]
        filename = "/".join(parts[1:])
        key = s3.Object(bucket, filename)
        state_file = key.get()["Body"].read().decode('utf-8')
        return json.loads(state_file)

    def get_terraform_state(self, state_file_url):
        tfstate = self._get_state_file_from_s3(state_file_url)
        for i in tfstate['modules']:
            if i['path'] == [u'root']:
                for key, value in i['outputs'].items():
                    self[key] = value

    def load_yaml(self, yml):
        self.get_terraform_state(yml['statefile'])
        self.lookups = yml['lookups']

    def lookup(self, attr, keys):
        return self[self.lookups[attr].format(**keys)]['value']

class TerraformE(dict):

    def __init__(self, yml, api_token=None):
        if api_token == None:
                if 'ATLAS_TOKEN' in os.environ:
                    self.api_token = os.getenv('ATLAS_TOKEN')
                else:
                    print("No Terraform Enterprise API token provided!")
        else:
            self.api_token = api_token

        self.organization = ''
        self.workspace = ''
        self.api_end_point = 'https://app.terraform.io/api/v2'

        self.load_yaml(yml)


    def load_yaml(self, yml):
        self.workspace = yml['workspace']
        self.organization = yml['organization']
        self.lookups = yml['lookups']
        self.list_state_versions()

    def list_state_versions(self):

        end_point = self.api_end_point + "/state-versions?"
        org_filter = "filter[organization][name]=" + self.organization
        workspace_filter = "filter[workspace][name]=" + self.workspace

        web_request = end_point + org_filter + "&" + workspace_filter

        headers = {'Authorization': 'Bearer ' + self.api_token,
                    'Content-Type': 'application/vnd.api+json'}

        response = requests.get(web_request, headers=headers)

        data = json.loads(response.text)
        state_download_url = data['data'][0]['attributes']['hosted-state-download-url']

        self.get_terraform_state(state_download_url)

    def get_terraform_state(self, state_download_url):
        response = requests.get(state_download_url)
        tfstate = json.loads(response.text)
        for i in tfstate['modules']:
            if i['path'] == [u'root']:
                for key, value in i['outputs'].items():
                    self[key] = value

    def lookup(self, attr, keys):
        return self[self.lookups[attr].format(**keys)]['value']
