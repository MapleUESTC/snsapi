#-*- encoding: utf-8 -*-

'''
renren client

Codes are adapted from following sources:
   * http://wiki.dev.renren.com/mediawiki/images/4/4c/Renren-oauth-web-demo-python-v1.0.rar
'''

from ..snslog import SNSLog
logger = SNSLog
from ..snsbase import SNSBase
from .. import snstype
from ..utils import console_output
from .. import utils


logger.debug("%s plugged!", __file__)

# Inteface URLs.
# This differs from other platforms
RENREN_AUTHORIZATION_URI = "http://graph.renren.com/oauth/authorize"
RENREN_ACCESS_TOKEN_URI = "http://graph.renren.com/oauth/token"
RENREN_SESSION_KEY_URI = "http://graph.renren.com/renren_api/session_key"
RENREN_API_SERVER = "http://api.renren.com/restserver.do"

class RenrenBase(SNSBase):

    # This error is moved back to "renren.py". 
    # It's platform specific and we do not expect other 
    # file to raise this error. 
    class RenrenAPIError(Exception):
        def __init__(self, code, message):
            super(RenrenAPIError, self).__init__(message)
            self.code = code

    def __init__(self, channel = None):
        super(RenrenBase, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        #c = super(RenrenBase).new_channel(full)
        c = SNSBase.new_channel(full)

        c['app_key'] = ''
        c['app_secret'] = ''
        c['platform'] = 'RenrenBase'
        c['auth_info'] = {
                "save_token_file": "(default)", 
                "cmd_request_url": "(default)", 
                "callback_url": "https://snsapi.ie.cuhk.edu.hk/aux/auth.php", 
                "cmd_fetch_code": "(default)" 
                } 

        return c

        
    def read_channel(self, channel):
        super(RenrenBase, self).read_channel(channel) 

        if not "callback_url" in self.auth_info: 
            self.auth_info.callback_url = "http://graph.renren.com/oauth/login_success.html"
        
    def auth_first(self):
        args = dict(client_id=self.jsonconf.app_key, redirect_uri = self.auth_info.callback_url)
        args["response_type"] = "code"
        args["scope"] = "read_user_status status_update publish_comment"
        args["state"] = "snsapi! Stand up, Geeks! Step on the head of those evil platforms!"
        url = RENREN_AUTHORIZATION_URI + "?" + self._urlencode(args)
        self.request_url(url)

    def auth_second(self):
        #TODO:
        #    The name 'fetch_code' is not self-explained.
        #    It actually fetches the authenticated callback_url.
        #    Code is parsed from this url. 
        url = self.fetch_code()
        self.token = self.parseCode(url)
        args = dict(client_id=self.jsonconf.app_key, redirect_uri = self.auth_info.callback_url)
        args["client_secret"] = self.jsonconf.app_secret
        args["code"] = self.token.code
        args["grant_type"] = "authorization_code"
        self.token.update(self._http_get(RENREN_ACCESS_TOKEN_URI, args))
        self.token.expires_in = self.token.expires_in + self.time()

    def auth(self):
        if self.get_saved_token():
            return

        logger.info("Try to authenticate '%s' using OAuth2", self.jsonconf.channel_name)
        self.auth_first()
        self.auth_second()
        self.save_token()
        logger.debug("Authorized! access token is " + str(self.token))
        logger.info("Channel '%s' is authorized", self.jsonconf.channel_name)

    def renren_request(self, params = None):
        """
        A general purpose encapsulation of renren API. 
        It fills in system paramters and compute the signature. 
        """

        #request a session key
        session_key_request_args = {"oauth_token": self.token.access_token}
        response = self._http_get(RENREN_SESSION_KEY_URI, session_key_request_args)
        session_key = str(response["renren_token"]["session_key"])

        #system parameters fill-in
        params["api_key"] = self.jsonconf.app_key
        params["call_id"] = str(int(self.time() * 1000))
        params["format"] = "json"
        params["session_key"] = session_key
        params["v"] = '1.0'
        # del 'sig' first, if not:
        #   Client may use the same params dict repeatedly. 
        #   Later call will fail because they have previous 'sig'. 
        if "sig" in params:
            del params["sig"] 
        sig = self.__hash_params(params);
        params["sig"] = sig
        
        try:
            response = self._http_post(RENREN_API_SERVER, params)
        finally:
            pass

        if type(response) is not list and "error_code" in response:
            logger.warning(response["error_msg"]) 
            raise RenrenBase.RenrenAPIError(response["error_code"], response["error_msg"])
        return response

    def __hash_params(self, params = None):
        import hashlib
        hashstring = "".join(["%s=%s" % (self._unicode_encode(x), self._unicode_encode(params[x])) for x in sorted(params.keys())])
        hashstring = hashstring + self._unicode_encode(self.jsonconf.app_secret)
        hasher = hashlib.md5(hashstring)
        return hasher.hexdigest()
        


class RenrenShare(RenrenBase):

    class Message(snstype.Message):
        def parse(self):
            self.ID.platform = self.platform
            self._parse_feed_share(self.raw)

        def _parse_feed_share(self, dct):
            self.ID.status_id = dct["source_id"]
            self.ID.source_user_id = dct["actor_id"]

            self.parsed.userid = dct['actor_id']
            self.parsed.username = dct['name']
            self.parsed.time = utils.str2utc(dct["update_time"], " +08:00")

            self.parsed.text_orig = dct['description']
            self.parsed.text_last = dct['message'] 
            self.parsed.text_trace = dct['trace']['text']
            self.parsed.title = dct['title']
            self.parsed.description = dct['description']
            self.parsed.reposts_count = 'N/A'
            self.parsed.comments_count = dct['comments']['count']

            self.parsed.text = self.parsed.text_trace \
                    + " || " + self.parsed.title \
                    + " || " + self.parsed.description

            #TODO: 
            #    retire past fileds. 
            #self.parsed.id = dct["source_id"]
            #self.parsed.created_at = dct["update_time"]
            #self.parsed.text = dct['message'] + " --> " + dct['description']
            #self.parsed.reposts_count = 'N/A'
            #self.parsed.comments_count = dct['comments']['count']
            #self.parsed.username = dct['name']
            #self.parsed.usernick = ""
            #self.ID.status_id = dct["source_id"]
            #self.ID.source_user_id = dct["actor_id"]

    def __init__(self, channel = None):
        super(RenrenShare, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform

    @staticmethod
    def new_channel(full = False):
        c = RenrenBase.new_channel(full)
        c['platform'] = 'RenrenShare'
        return c
        
    def home_timeline(self, count=20):
        '''Get home timeline
        get statuses of yours and your friends'
        @param count: number of statuses
        '''

        api_params = dict(method = "feed.get", \
                type = "21,32,33,50,51,52", \
                page = 1, count = count)
        jsonlist = self.renren_request(api_params)
        
        statuslist = []
        try:
            for j in jsonlist:
                statuslist.append(self.Message(j,\
                        platform = self.jsonconf['platform'],\
                        channel = self.jsonconf['channel_name']\
                        ))
        except Exception, e:
            logger.warning("catch expection:%s", e.message)

        logger.info("Read %d statuses from '%s'", len(statuslist), self.jsonconf.channel_name)
        return statuslist

    def reply(self, statusID, text):
        """reply status
        @param status: StatusID object
        @param text: string, the reply message
        @return: success or not
        """

        api_params = dict(method = "share.addComment", content = text, \
            share_id = statusID.status_id, user_id = statusID.source_user_id)

        try:
            ret = self.renren_request(api_params)
            if 'result' in ret and ret['result'] == 1:
                logger.info("Reply '%s' to status '%s' succeed", text, statusID)
                return True
        except:
            pass

        logger.info("Reply '%s' to status '%s' fail", text, statusID)
        return False

class RenrenStatus(RenrenBase):

    class Message(snstype.Message):
        def parse(self):
            self.ID.platform = self.platform
            self._parse_feed_status(self.raw)

        def _parse_feed_status(self, dct):
            #logger.debug(json.dumps(dct))
            # By trial, it seems:
            #    * 'post_id' : the id of news feeds
            #    * 'source_id' : the id of status
            #      equal to 'status_id' returned by 
            #      'status.get' interface
            # self.id = dct["post_id"]

            self.ID.status_id = dct["source_id"]
            self.ID.source_user_id = dct["actor_id"]

            self.parsed.userid = dct['actor_id']
            self.parsed.username = dct['name']
            self.parsed.time = utils.str2utc(dct["update_time"], " +08:00")
            self.parsed.text = dct['message']

            #print dct 

            try:
                self.parsed.username_orig = dct['attachment'][0]['owner_name']
                self.parsed.text_orig = dct['attachment'][0]['content']
                self.parsed.text += " || " + "@" + self.parsed.username_orig \
                        + " : " + self.parsed.text_orig
                #print self.parsed.text
            except:
                pass
            #except Exception, e:
            #    raise e

            self.parsed.text_trace = dct['message'] 
            self.parsed.reposts_count = 'N/A'
            self.parsed.comments_count = dct['comments']['count']

            #self.parsed.id = dct["source_id"]
            #self.parsed.created_at = dct["update_time"]
            #self.parsed.text = dct['message']
            #self.parsed.reposts_count = 'N/A'
            #self.parsed.comments_count = dct['comments']['count']
            #self.parsed.username = dct['name']
            #self.parsed.usernick = ""
            #self.ID.status_id = dct["source_id"]
            #self.ID.source_user_id = dct["actor_id"]

        # The following is to parse Status of Renren. 
        # (get by invoking 'status.get', not 'feed.get')
        #def _parse_status(self, dct):
        #    self.id = dct["status_id"]
        #    self.created_at = dct["time"]
        #    if 'root_message' in dct:
        #        self.text = dct['root_message']
        #    else:
        #        self.text = dct['message']
        #    self.reposts_count = dct['forward_count']
        #    self.comments_count = dct['comment_count']
        #    self.username = dct['uid']
        #    self.usernick = ""

    def __init__(self, channel = None):
        super(RenrenStatus, self).__init__(channel)

        self.platform = self.__class__.__name__
        self.Message.platform = self.platform
        
    @staticmethod
    def new_channel(full = False):
        c = RenrenBase.new_channel(full)
        c['platform'] = 'RenrenStatus'
        return c
        
    def home_timeline(self, count=20):
        '''Get home timeline
        get statuses of yours and your friends'
        @param count: number of statuses
        '''

        api_params = dict(method = "feed.get", type = 10, page = 1, count = count)
        jsonlist = self.renren_request(api_params)
        
        statuslist = []
        try:
            for j in jsonlist:
                statuslist.append(self.Message(j,\
                        platform = self.jsonconf['platform'],\
                        channel = self.jsonconf['channel_name']\
                        ))
        except Exception, e:
            logger.warning("catch expection:%s", e.message)

        logger.info("Read %d statuses from '%s'", len(statuslist), self.jsonconf.channel_name)
        return statuslist

    def update(self, text):
        '''update a status
        @param text: the update message
        @return: success or not
        '''

        api_params = dict(method = "status.set", status = text)
        
        try:
            ret = self.renren_request(api_params)
            if 'result' in ret and ret['result'] == 1:
                logger.info("Update status '%s' on '%s' succeed", text, self.jsonconf.channel_name)
                return True
        except:
            pass

        logger.info("Update status '%s' on '%s' fail", text, self.jsonconf.channel_name)
        return False

    def reply(self, statusID, text):
        """reply status
        @param status: StatusID object
        @param text: string, the reply message
        @return: success or not
        """

        #TODO: check platform and place a warning
        #      if it is not "renren"

        api_params = dict(method = "status.addComment", content = text, \
            status_id = statusID.status_id, owner_id = statusID.source_user_id)

        try:
            ret = self.renren_request(api_params)
            if 'result' in ret and ret['result'] == 1:
                logger.info("Reply '%s' to status '%s' succeed", text, statusID)
                return True
        except:
            pass

        logger.info("Reply '%s' to status '%s' fail", text, statusID)
        return False
