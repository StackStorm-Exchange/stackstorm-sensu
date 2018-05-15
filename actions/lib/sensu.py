import json

from st2common.runners.base_action import Action
from pysensu.api import SensuAPI


def parseOutput(r):
    try:
        output = {}
        json.loads(r.text)
        for c in r.json():
            output[c['name']] = c
        return json.dumps(output)
    except Exception:
        return r.text


class SensuAction(Action):
    def __init__(self, config):
        super(SensuAction, self).__init__(config)
        self.username = self.config['user']
        self.password = self.config['pass']
        if self.config['ssl']:
            protocol = 'https'
        else:
            protocol = "http"
        self.base_url = "%s://%s:%s" % (protocol, self.config['host'], self.config['port'])

        self.api = SensuAPI(url_base=self.base_url, username=self.username, password=self.password)
