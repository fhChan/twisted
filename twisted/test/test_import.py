from pyunit import unittest

class AtLeastImportTestCase(unittest.TestCase):
    
    """I test that there are no syntax errors which will not allow importing.
    """
    def testImport(self):
        """Test all imports.
        """
        from twisted import copyright
        
        from twisted.python import authenticator
        from twisted.python import delay
        from twisted.python import hook
        from twisted.python import log
        from twisted.python import observable
        
        from twisted.persisted import dirdbm

        from twisted.protocols import ftp
        from twisted.spread import jelly
        from twisted.persisted import styles
        
        from twisted.internet import tcp
        from twisted.internet import main
        # from twisted.internet import ssl
        from twisted.internet import stdio
        from twisted.internet import abstract
        from twisted.internet import process
        
        from twisted.spread import pb
        from twisted.reality import plumbing
        from twisted.python import reference
        from twisted.python import reflect
        from twisted.protocols import telnet
        from twisted.python import threadable
        from twisted.python import threadpool
        from twisted.python import usage
        from twisted.python import worker

        # TR imports
        from twisted.reality import reality
        from twisted.reality import thing
        from twisted.reality import sentence
        from twisted.reality import source
        from twisted.reality import error
        from twisted.reality import player
        from twisted.reality import room
        from twisted.reality import container
        from twisted.reality import geometry
        from twisted.reality import clothing
        from twisted.reality import door
        from twisted.reality import furniture
        from twisted.reality import lock

        # TP library
        from twisted.protocols import basic
        from twisted.protocols import http
        from twisted.protocols import irc
        from twisted.protocols import pop3
        from twisted.protocols import protocol
        from twisted.protocols import smtp
        from twisted.protocols import telnet

        # TW library

        from twisted.web import server
        from twisted.web import html
        from twisted.web import twcgi
        ## from twisted.web import distributed
        from twisted.web import calendar
        from twisted.web import script
        from twisted.web import static
        from twisted.web import test
        from twisted.web import utils
        from twisted.web import vhost
        from twisted.web import weblog

        

testCases = [AtLeastImportTestCase]
