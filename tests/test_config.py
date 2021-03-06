#-*-coding:utf-8-*-

"""
Nosetest configs 

The layout of nosetest is learned from: 
   wong2/xiaohuangji-new
"""

import os
import glob
import sys
import json


DIR_TEST = os.path.abspath(os.path.dirname(__file__))
DIR_ROOT = os.path.dirname(DIR_TEST)
DIR_CONF = os.path.join(DIR_ROOT, "conf")
DIR_SNSAPI = os.path.join(DIR_ROOT, "snsapi")
DIR_PLUGIN = os.path.join(DIR_SNSAPI, "plugin")

# Result refers to result returned by plugin
#WRONG_KEY_WORD_ERROR = "Missing or wrong keyword should not have result."
#WRONG_RESULT_FORMAT_ERROR = "Result should have correct format."
WRONG_RESULT_ERROR = "Correct keyword should have result."

class TestBase(object):

    @classmethod
    def clean_up(klass, path, wildcard):
        os.chdir(path)
        for rm_file in glob.glob(wildcard):
            os.unlink(rm_file)

    @classmethod
    def setup_class(klass):
        sys.stderr.write("\nRunning %s\n" % klass)

    @classmethod
    def teardown_class(klass):
        klass.clean_up(DIR_TEST, "*.py?")
        klass.clean_up(DIR_SNSAPI, "*.py?")
        klass.clean_up(DIR_PLUGIN, "*.py?")
        klass.clean_up(DIR_ROOT, "*.py?")

# ===== old funcs from testUtils.py ======
    
def get_config_paths():
    '''
    How to get the path of config.json in test directory, Use this. 
    '''
    paths = {
            'channel': os.path.join(DIR_CONF, 'channel.json'), 
            'snsapi': os.path.join(DIR_CONF, 'snsapi.json')
            }
    return paths

def get_channel(platform):
    paths = get_config_paths()
    with open(paths['channel']) as fp:
        channel = json.load(fp)
        
    for site in channel:
        if site['platform'] == platform:
            return site
        
    raise TestInitNoSuchPlatform(platform)

def clean_saved_token():
    import os,glob
    for f in glob.glob('*.token.save'):
        os.remove(f)

class TestInitError(Exception):
    """docstring for TestInitError"""
    def __init__(self):
        super(TestInitError, self).__init__()
    def __str__(self):
        print "Test init error. You may want to check your configs."

class TestInitNoSuchPlatform(TestInitError):
    def __init__(self, platform = None):
        self.platform = platform
    def __str__(self):
        if self.platform is not None:
            print "Test init error -- No such platform : %s. " \
            "Please check your channel.json config. " % self.platform
        
if __name__ == '__main__':
    print DIR_TEST
    print DIR_ROOT
    print DIR_CONF
    print DIR_SNSAPI
    print get_config_paths()
