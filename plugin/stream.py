"""
GREEK STREAM TV

Ideas & Sources:
StreamTV (Black Hole image)
https://github.com/chrippa/livestreamer
http://code.google.com/p/airplayer/source/browse/trunk/AirPlayer/mediabackends/e2_media_backend.py
https://github.com/DonDavici/DreamPlex/blob/master/src/DP_Player.py
http://code.google.com/p/archivy-czsk/source/browse/trunk/engine/player/player.py?r=77
...all others...

"""

import os
import ssl
from sys import path
from time import sleep
try:
    from _thread import start_new_thread
except ImportError:
    from thread import start_new_thread
from xml.etree.cElementTree import ElementTree

from . import _
from enigma import eTimer, ePicLoad, eServiceReference, iPlayableService, iServiceInformation
from enigma import gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarAudioSelection, InfoBarNotifications
from skin import parseFont
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.GUIComponent import GUIComponent
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Components.ServiceEventTracker import ServiceEventTracker
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from streamlink import Streamlink


PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/GreekStreamTV")
path.append(PLUGIN_PATH)


class SelectQuality(Screen):
    skin = """
        <screen name="SelectQuality" position="center,center" size="280,180" title="Select quality">
            <widget name="menu" position="0,0" size="270,120" itemHeight="40" font="Body" textOffset="10,0" scrollbarMode="showOnDemand"/>
            <widget name="info" position="0,140" size="270,40" font="Body" halign="center" valign="center"/>
        </screen>"""

    def __init__(self, session, streams, selectedFunc, enableWrapAround=False):
        Screen.__init__(self, session)
        self.setTitle(_("Select quality"))
        self["info"] = Label("...")
        self.selectedFunc = selectedFunc
        menu = [ (str(sn[0]), sn[1]) for sn in list(streams.items()) ]
        self["menu"] = MenuList(menu, enableWrapAround)
        self["actions"] = ActionMap(["OkCancelActions"],
        {
            "ok": self.okbuttonClick,
            "cancel": self.cancelClick
        }, -1)

    def getCurrent(self):
        cur = self["menu"].getCurrent()
        return cur and cur[1]

    def okbuttonClick(self):
        self["info"].setText(_("Please wait..."))
        self.timer = eTimer()
        self.timer.callback.append(self.StartStreaming)
        self.timer.start(100, 1)

    def StartStreaming(self):
        self.timer.stop()
        self.selectedFunc(self.getCurrent())

    def up(self):
        self["menu"].up()

    def down(self):
        self["menu"].down()

    def cancelClick(self):
        self.close(False)


class GreekStreamTVPlayer(Screen, InfoBarAudioSelection, InfoBarNotifications):
    skin = """
        <screen name="GreekStreamTVPlayer" flags="wfNoBorder" position="center, e-120" size="e,120" title="GreekStreamTV player">
            <ePixmap position="40,25" size="117,72" pixmap="%s/icons/channel_background.png" zPosition="-1" alphatest="blend"/>
            <widget name="channel_icon" position="81,43" zPosition="10" size="35,35"/>
            <widget name="channel_name" position="center,20" size="e-400,40" font="Body" halign="center" valign="center"/>
            <widget name="channel_uri" position="center,70" size="e-400,30" font="Regular;22" halign="center" valign="center"/>
            <widget source="session.CurrentService" render="Label" position="e-160,20" size="120,40" font="Body" halign="right" valign="center">
                <convert type="ServicePosition">Position,ShowHours</convert>
            </widget>
        </screen>""" % (PLUGIN_PATH)

    PLAYER_IDLE    = 0
    PLAYER_PLAYING = 1
    PLAYER_PAUSED  = 2

    def __init__(self, session, service, stopPlayer, chName, chURL, chIcon):
        Screen.__init__(self, session)
        InfoBarAudioSelection.__init__(self)
        InfoBarNotifications.__init__(self)

        isEmpty = lambda x: x is None or len(x) == 0 or x == "None"
        if isEmpty(chName): chName = "Unknown"
        if isEmpty(chURL):  chURL  = "Unknown"
        if isEmpty(chIcon): chIcon = "default.png"
        chIcon = "%s/icons/%s" % (PLUGIN_PATH, chIcon)
        self.service = service
        self.stopPlayer = stopPlayer

        self.setTitle(chName)
        self["channel_icon"] = Pixmap()
        self["channel_name"] = Label(chName)
        self["channel_uri"]  = Label(chURL)

        self["actions"] = ActionMap(["OkCancelActions", "InfobarSeekActions", "MediaPlayerActions", "MovieSelectionActions"],
        {
            "ok": self.doInfoAction,
            "cancel": self.doExit,
            "stop": self.doExit,
            "playpauseService": self.playpauseService,
        }, -2)

        self.__event_tracker = ServiceEventTracker(screen = self, eventmap = {
            iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
            iPlayableService.evStart: self.__serviceStarted,
            iPlayableService.evEOF: self.__evEOF,
            iPlayableService.evUser + 10: self.__evAudioDecodeError,
            iPlayableService.evUser + 11: self.__evVideoDecodeError,
            iPlayableService.evUser + 12: self.__evPluginError,
        })

        self.hidetimer = eTimer()
        self.hidetimer.timeout.get().append(self.doInfoAction)

        self.state = self.PLAYER_IDLE
        self.__seekableStatusChanged()

        self.onClose.append(self.__onClose)
        self.doPlay()

        self.picload = ePicLoad()
        self.scale = AVSwitch().getFramebufferScale()
        self.picload.PictureData.get().append(self.cbDrawChannelIcon)
        self.picload.setPara((35, 35, self.scale[0], self.scale[1], False, 0, "#00000000"))
        self.picload.startDecode(chIcon)

    def cbDrawChannelIcon(self, picInfo=None):
        ptr = self.picload.getData()
        if ptr != None:
            self["channel_icon"].instance.setPixmap(ptr.__deref__())
            self["channel_icon"].show()

    def __onClose(self):
        self.session.nav.stopService()

    def __seekableStatusChanged(self):
        service = self.session.nav.getCurrentService()
        if service is not None:
            seek = service.seek()
            if seek is None or not seek.isCurrentlySeekable():
                self.setSeekState(self.PLAYER_PLAYING)

    def __serviceStarted(self):
        self.state = self.PLAYER_PLAYING
        self.__seekableStatusChanged()

    def __evEOF(self):
        self.doExit()

    def __evAudioDecodeError(self):
        currPlay = self.session.nav.getCurrentService()
        sAudioType = currPlay.info().getInfoString(iServiceInformation.sUser + 10)
        print("[__evAudioDecodeError] audio-codec %s can't be decoded by hardware" % (sAudioType))
        self.session.open(MessageBox, _("This receiver can't decode %s streams!") % sAudioType, type=MessageBox.TYPE_INFO, timeout=10)

    def __evVideoDecodeError(self):
        currPlay = self.session.nav.getCurrentService()
        sVideoType = currPlay.info().getInfoString(iServiceInformation.sVideoType)
        print("[__evVideoDecodeError] video-codec %s can't be decoded by hardware" % (sVideoType))
        self.session.open(MessageBox, _("This receiver can't decode %s streams!") % sVideoType, type=MessageBox.TYPE_INFO, timeout=10)

    def __evPluginError(self):
        currPlay = self.session.nav.getCurrentService()
        message = currPlay.info().getInfoString(iServiceInformation.sUser + 12)
        print("[__evPluginError]" , message)
        self.session.open(MessageBox, message, type=MessageBox.TYPE_INFO, timeout=10)

    def __setHideTimer(self):
        self.hidetimer.start(5000)

    def doExit(self):
        print("[GreekStreamTVPlayer::doExit]")
        self.stopPlayer()
        self.close()

    def setSeekState(self, wantstate):
        service = self.session.nav.getCurrentService()
        if service is None:
            print("[GreekStreamTV:: ::setSeekState] No Service found")
            return

        pauseable = service.pause()
        if pauseable is not None:
            if wantstate == self.PLAYER_PAUSED:
                pauseable.pause()
                self.state = self.PLAYER_PAUSED
                if not self.shown:
                    self.hidetimer.stop()
                    self.show()
            elif wantstate == self.PLAYER_PLAYING:
                pauseable.unpause()
                self.state = self.PLAYER_PLAYING
                if self.shown:
                    self.__setHideTimer()
        else:
            self.state = self.PLAYER_PLAYING

    def doInfoAction(self):
        if self.shown:
            self.hidetimer.stop()
            self.hide()
        else:
            self.show()
            if self.state == self.PLAYER_PLAYING:
                self.__setHideTimer()

    def doPlay(self):
        if self.state == self.PLAYER_PAUSED:
            if self.shown:
                self.__setHideTimer()
        self.state = self.PLAYER_PLAYING
        self.session.nav.playService(self.service)
        if self.shown:
            self.__setHideTimer()

    def playpauseService(self):
        print("[GreekStreamTVPlayer::playpauseService] State ", self.state)
        if self.state == self.PLAYER_PLAYING:
            self.setSeekState(self.PLAYER_PAUSED)
        elif self.state == self.PLAYER_PAUSED:
            self.setSeekState(self.PLAYER_PLAYING)


class StreamURIParser:
    def __init__(self, xml):
        self.xml = xml

    def parseStreamList(self):
        tvlist = []
        tree = ElementTree()
        tree.parse(self.xml)
        for iptv in tree.findall("iptv"):
            tvlist.append({
                "name" : str(iptv.findtext("name")).title(),
                "icon" : str(iptv.findtext("icon")),
                "type" : str(iptv.findtext("type")),
                "uri"  : self.parseStreamURI(str(iptv.findtext("uri")))
            })
        return sorted(tvlist, key=lambda item: item["name"])

    def parseStreamURI(self, uri):
        uriInfo = {}
        splitedURI = uri.split()
        uriInfo["URL"] = splitedURI[0]
        for x in splitedURI[1:]:
            i = x.find("=")
            uriInfo[x[:i]] = str(x[i+1:])
        return uriInfo


class StreamList(MenuList):
    def __init__(self, streamList):
        MenuList.__init__(self, streamList, True, eListboxPythonMultiContent)
        self.l.setBuildFunc(self.streamListEntry)

        # default skin parameters
        self.serviceNameFont = gFont("Regular", 22)
        self.serviceUrlFont = gFont("Regular", 20)
        self.itemHeight = 37
        self.serviceNamePosition = (45,0)
        self.serviceNameSize = (300,37)
        self.serviceUrlPosition = (350,0)
        self.serviceUrlSize = (430,37)
        self.iconPosition = (5,1)
        self.iconSize = (35,35)

    def applySkin(self, desktop, parent):
        def warningWrongSkinParameter(string):
            print("[StreamList] wrong '%s' skin parameter" % string)
        def itemHeight(value):
            self.itemHeight = int(value)
        def serviceNameFont(value):
            self.serviceNameFont = parseFont(value, ((1,1),(1,1)))
        def serviceUrlFont(value):
            self.serviceUrlFont = parseFont(value, ((1,1),(1,1)))
        def serviceNamePosition(value):
            pos = list(map(int, value.split(',')))
            if len(pos) == 2:
                self.serviceNamePosition = pos
            else:
                warningWrongSkinParameter(attrib)
        def serviceNameSize(value):
            size = list(map(int, value.split(',')))
            if len(size) == 2:
                self.serviceNameSize = size
            else:
                warningWrongSkinParameter(attrib)
        def serviceUrlPosition(value):
            pos = list(map(int, value.split(',')))
            if len(pos) == 2:
                self.serviceUrlPosition = pos
            else:
                warningWrongSkinParameter(attrib)
        def serviceUrlSize(value):
            size = list(map(int, value.split(',')))
            if len(size) == 2:
                self.serviceUrlSize = size
            else:
                warningWrongSkinParameter(attrib)
        def iconPosition(value):
            pos = list(map(int, value.split(',')))
            if len(pos) == 2:
                self.iconPosition = pos
            else:
                warningWrongSkinParameter(attrib)
        def iconSize(value):
            size = list(map(int, value.split(',')))
            if len(size) == 2:
                self.iconSize = size
            else:
                warningWrongSkinParameter(attrib)
        for (attrib, value) in self.skinAttributes[:]:
            try:
                locals().get(attrib)(value)
                self.skinAttributes.remove((attrib, value))
            except:
                pass
        self.l.setItemHeight(self.itemHeight)
        self.l.setFont(0, self.serviceNameFont)
        self.l.setFont(1, self.serviceUrlFont)
        return GUIComponent.applySkin(self, desktop, parent)

    def streamListEntry(self, name, entry):
        uriInfo = entry.get("uri")
        url = str(uriInfo.get("URL"))
        icon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/GreekStreamTV/%s" % str(entry.get("icon"))))
        if icon is None: # fallback to icon supplied by the plugin
            icon = LoadPixmap(resolveFilename(SCOPE_CURRENT_PLUGIN, "%s/icons/%s" % (PLUGIN_PATH, str(entry.get("icon")))))

        return [ None, # no private data
            MultiContentEntryPixmapAlphaBlend(self.iconPosition, self.iconSize, icon),
            MultiContentEntryText(self.serviceNamePosition, self.serviceNameSize, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, str(name)),
            MultiContentEntryText(self.serviceUrlPosition, self.serviceUrlSize, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, url)
        ]


class GreekStreamTVList(Screen):

    skin = """
        <screen name="GreekStreamTVList" position="center,center" size="3*e/4,3*e/4" title="GreekStreamTV list">
            <widget name="streamlist" position="0,10" size="e,e-100" itemHeight="40" scrollbarMode="showOnDemand"/>
            <widget name="info" position="0,e-80" size="e,40" font="Regular;20" halign="center" valign="center"/>
            <ePixmap pixmap="buttons/key_red.png" position="0,e-40" size="40,40" alphatest="blend"/>
            <ePixmap pixmap="buttons/key_green.png" position="e/4,e-40" size="40,40" alphatest="blend"/>
            <widget source="key_red" render="Label" position="40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
            <widget source="key_green" render="Label" position="e/4+40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
        </screen>"""

    def __init__(self, session, streamFile=None):
        Screen.__init__(self, session)
        self.setTitle(_("GreekStreamTV list"))
        self["info"] = Label("...")
        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Play"))

        self["actions"] = ActionMap(["OkCancelActions", "WizardActions", "ColorActions"],
        {
            "ok"    : self.keyOK,
            "green" : self.keyOK,
            "cancel": self.keyCancel,
            "red"   : self.keyCancel,
            "up"    : self.keyUp,
            "down"  : self.keyDown,
            "left"  : self.keyLeft,
            "right" : self.keyRight,
        }, -1)

        self.streamBin  = "/usr/bin/rtmpdump"
        self.streamPipe = "/tmp/greekstreamtv.avi"

        if not streamFile:
            self.streamFile = resolveFilename(SCOPE_PLUGINS, "Extensions/GreekStreamTV/stream.xml")
        else:
            self.streamFile = streamFile

        self.lvstreamer = Streamlink()

        self.streamList = []
        self.makeStreamList()
        self["streamlist"] = StreamList(self.streamList)

        self.onLayoutFinish.append(self.layoutFinished)

        self.beforeService  = None
        self.currentService = None
        self.playerStoped   = False
        self.keyLocked = False
        self.pd = None
        self.qsel = None

    def layoutFinished(self):
        os.system("killall -9 rtmpdump")
        self.showName()

    def keyLeft(self):
        if self.keyLocked:
            return
        self["streamlist"].pageUp()
        self.showName()

    def keyRight(self):
        if self.keyLocked:
            return
        self["streamlist"].pageDown()
        self.showName()

    def keyUp(self):
        if self.keyLocked:
            return
        self["streamlist"].up()
        self.showName()

    def keyDown(self):
        if self.keyLocked:
            return
        self["streamlist"].down()
        self.showName()

    def keyCancel(self):
        self.LivestreamerStop()
        if PLUGIN_PATH in path:
            path.remove(PLUGIN_PATH)
        self.close()

    def showName(self):
        try:
            tmpName = self["streamlist"].getCurrent()[1].get("name")
        except:
            tmpName = "..."
        self["info"].setText(tmpName)

    def keyOK(self):
        print("[GreekStreamTVList::keyOK]")
        if self.keyLocked:
            return

        uriName = self["streamlist"].getCurrent()[1].get("name")
        self["info"].setText(_("Starting %s\n\nPlease wait...") % uriName)
        self.timer = eTimer()
        self.timer.callback.append(self.StartStream)
        self.timer.start(100, 1)

    def StartStream(self):
        self.timer.stop()
        self.keyLocked      = True
        self.beforeService  = None
        self.currentService = None
        self.playerStoped   = False
        self.pd             = None

        streamInfo  = self["streamlist"].getCurrent()[1]
        uriInfo     = streamInfo.get("uri")
        typeInfo    = streamInfo.get("type").split(":")
        protocol    = typeInfo[0]
        serviceType = typeInfo[1]
        bufferSize  = typeInfo[2]
        url         = uriInfo.get("URL")

        if protocol == "rtmp":
            url += " "
            url += " ".join(["%s=%s" % (key, value) for (key, value) in list(uriInfo.items()) if key != "URL"])
            url = " ".join(url.split())
            print("[GreekStreamTVList::keyOK] URL is ", url, " URI is ", uriInfo)
            self.doStreamAction(url, serviceType, bufferSize)
        elif protocol in ("rtsp", "http"):
            self.doStreamAction(url, serviceType, bufferSize)
        elif protocol == "livestreamer":
            streams = None
            try:
                url += " "
                url += " ".join(["%s=%s" % (key, value) for (key, value) in list(uriInfo.items()) if key != "URL"])
                url = " ".join(url.split())
                print("[GreekStreamTVList::keyOK] URL is ", url, " URI is ", uriInfo)
                streams = self.lvstreamer.streams(url)
                print("[GreekStreamTVList::keyOK] Streams: ", list(streams.keys()))
                print("[GreekStreamTVList::keyOK] Streams: ", list(streams.items()))
                if len(streams) == 3 and "best" in streams and "worst" in streams:
                    self.streamPreBuffer(streams["best"])
                elif len(streams) == 0:
                    raise Exception("No Streams Found")
                else:
                    self.qsel = self.session.openWithCallback(self.QualitySelClosed, SelectQuality, streams, self.streamPreBuffer)
            except Exception as err:
                print("[GreekStreamTVList::keyOK::Exception] Error: %s" % err)
                tmpMessage = _("An error occured: ") + str(err)[:200] + "..."
                self.session.openWithCallback(self.stopPlayer, MessageBox, tmpMessage, type=MessageBox.TYPE_ERROR, timeout=10)
        else:
            print("[GreekStreamTVList::keyOK] Unknown Protocol: ", protocol)
            tmpMessage = _("Unknown protocol: ") + protocol
            self.session.openWithCallback(self.stopPlayer, MessageBox, tmpMessage, type=MessageBox.TYPE_WARNING, timeout=10)

    def QualitySelClosed(self, recursive):
        if self.qsel:
            self.qsel.close()
        self.qsel = None
        self.stopPlayer()

    def streamPreBuffer(self, stream):
        fd = None
        try:
            fd = stream.open()
            prebuffer = fd.read(8196 * 128) #PREBUFFER
            if len(prebuffer) == 0:
               raise Exception("No Data Received From Stream Server")
            start_new_thread(self.streamCopy, (fd,prebuffer))
            sleep(1.5)
            self.doStreamAction(self.streamPipe)
        except Exception as err:
            if fd and hasattr(fd, "close"):
                fd.close()
            print("[GreekStreamTVList::streamPreBuffer::Exception] Error: %s" % err)
            tmpMessage = _("An error occured while buffering: ") + str(err)[:200] + "..."
            self.session.openWithCallback(self.stopPlayer, MessageBox, tmpMessage, type=MessageBox.TYPE_ERROR, timeout=10)

    def streamCopy(self, fd, prebuffer):
        print("[GreekStreamTVList::streamCopy]")
        if os.access(self.streamPipe, os.F_OK):
            os.remove(self.streamPipe)
        os.mkfifo(self.streamPipe)
        self.pd = open(self.streamPipe, "wb")
        try:
            self.pd.write(prebuffer)
            while self is not None and self.session is not None and not self.playerStoped:
                data = fd.read(8192)
                if len(data) == 0:
                    break
                self.pd.write(data)
            print("[GreekStreamTVList:streamCopy] playerStoped")
            self.pd.close()
            if hasattr(fd, "close"):
                fd.close()
            fd = None
        except Exception as err:
            print("[GreekStreamTVList::streamCopy] Exception: %s" % err)
        finally:
            self.playerStoped = True
            if fd and hasattr(fd, "close"):
                fd.close()

    def LivestreamerStop(self):
        print("[GreekStreamTVList::LivestreamStop]")
        self.showName()
        self.keyLocked = False
        self.playerStoped = True
        os.system("killall -9 rtmpdump")
        sleep(0.5)
        if self.pd:
            try: self.pd.close()
            except:
                sleep(0.5)
                try: self.pd.close()
                except: pass
        if self.qsel is not None:
            self.qsel.close(False)
        self.pd   = None
        self.qsel = None

    def doStreamAction(self, url=None, serviceType=4097, bufferSize=None):
        if url is None:
            url=self.streamPipe
            self.streamPlayerTimer.stop()

        try: serviceType = int(serviceType)
        except: serviceType = 4097
        try: bufferSize = int(bufferSize)
        except: bufferSize = None

        service = eServiceReference(serviceType, 0, url)

        #if bufferSize is not None:
        #    service.setData(2, bufferSize*1024)

        streamInfo = self["streamlist"].getCurrent()[1]
        service.setName(str(streamInfo.get("name")))
        uriInfo    = streamInfo.get("uri")

        self.beforeService  = self.session.nav.getCurrentlyPlayingServiceReference()
        self.currentService = self.session.openWithCallback(self.onStreamFinished,
                                    GreekStreamTVPlayer,
                                    service,
                                    stopPlayer=self.stopPlayer,
                                    chName=str(streamInfo.get("name")),
                                    chURL =str(uriInfo.get("URL")),
                                    chIcon=str(streamInfo.get("icon")))

    def stopPlayer(self, params=None):
        print("[GreekStreamTV::stopPlayer]")
        if params is None or isinstance(params, bool):
            self.playerStoped = True
            self.LivestreamerStop()
            return

    def onStreamFinished(self):
        print("[GreekStreamTV::onStreamFinished]")
        self.LivestreamerStop()
        self.session.nav.playService(self.beforeService)
        print("[GreekStreamTV::onStreamFinished] player done!!")

    def makeStreamList(self):
        try: streamDB = StreamURIParser(self.streamFile).parseStreamList()
        except Exception as err:
            print("[GreekStreamTV::makeStreamList] Error: %s" % err)
            streamDB = []
        self.streamList = [ (x.get("name"), x) for x in streamDB ]
