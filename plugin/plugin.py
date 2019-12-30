from os import path, listdir

from . import _
from Plugins.Plugin import PluginDescriptor
from Components.MenuList import MenuList
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.Console import Console


url_sc = "/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV/update.sh"
url_pd = "/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV/depends.sh"

GSXML = "/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV/stream.xml"
GSBQ = "/etc/enigma2/userbouquet.greekstreamtv.tv"


def main(session, **kwargs):
    try:
        session.open(GSMenu)
    except:
        print "[GreekStreamTV] Plugin execution failed"


def autostart(reason, **kwargs):
    if reason == 0:
        print "[GreekStreamTV] no autostart"


def Plugins(**kwargs):
    return PluginDescriptor(
        name=_("GreekStreamTV"),
        where=[PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_PLUGINMENU],
        description=_("Watch live stream TV"),
        icon="plugin.png",
        fnc=main)


class GSMenu(Screen):
    skin = """
        <screen name="GSMenu" position="center,center" size="560,430" title="GreekStreamTV">
            <widget name="menu" itemHeight="35" position="10,50" size="540,360" scrollbarMode="showOnDemand" transparent="1" zPosition="9"/>
            <ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on"/>
            <ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on"/>
            <ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on"/>
            <ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphatest="on"/>
            <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
            <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
            <widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
            <widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>
        </screen>
        """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(_("GreekStreamTV"))

        self["key_red"] = StaticText(_("Close"))
        self["key_green"] = StaticText(_("Select"))
        self["key_yellow"] = StaticText(_("Install dependencies"))
        self["key_blue"] = StaticText(_("About"))

        menu = []
        if path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV"):
            menu.append((_("GreekStreamTV"), GSXML))
            menu.extend(self.getStreams())
            menu.append((_("Update stations"), "update"))
            if path.isfile(GSBQ):
                menu.append((_("Update bouquet"), "updatebq"))

        self["menu"] = MenuList(menu)
        self["actions"] = ActionMap(["ColorActions", "OkCancelActions"],
        {
            "cancel": self.close,
            "red": self.close,
            "ok": self.go,
            "green": self.go,
            "yellow": self.yellow,
            "blue": self.blue,
        }, -1)

    def go(self):
        if self["menu"].getCurrent() is not None:
            choice = self["menu"].getCurrent()[1]
            if choice.endswith(".xml"):
                try:
                    from Plugins.Extensions.GreekStreamTV.stream import main
                    main(self.session, streamFile = choice)
                except Exception as err:
                    print "[GreekStreamTV::PluginMenu] Exception: ", str(err)
                    import traceback
                    traceback.print_exc()
                    msg = _("Error loading plugin!")
                    msg += "\n\n"
                    msg += _("Error: ")
                    msg += str(err)[:200] + "...\n"
                    msg += _("Installing the necessary dependencies might solve the problem...")
                    self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
            elif choice == "update":
                msg = _("Do you really want to update the list of stations?")
                self.session.openWithCallback(self.update, MessageBox, msg, MessageBox.TYPE_YESNO)
            elif choice == "updatebq":
                try:
                    self.updatebq()
                    from enigma import eDVBDB
                    eDVBDB.getInstance().reloadBouquets()
                    eDVBDB.getInstance().reloadServicelist()
                    tmpMessage = _("GreekStreamTV bouquet updated successfully...")
                except Exception as err:
                    print "[GreekStreamTV::PluginMenu] Exception: ", str(err)
                    tmpMessage = _("GreekStreamTV bouquet update failed...")
                self.session.open(MessageBox, tmpMessage, MessageBox.TYPE_INFO)

    def updatebq(self):
        from xml.etree.cElementTree import ElementTree
        tree = ElementTree()
        tree.parse(GSXML)
        tvlist = []
        for iptv in tree.findall("iptv"):
            name = iptv.findtext("name").title()
            (protocol, serviceType, bufferSize, epgId) = iptv.findtext("type").split(":")
            uri = iptv.findtext("uri")
            if protocol in "livestreamer":
                uri = "http://localhost:88/" + uri
            uri = uri.replace(":", "%3a")
            service = "#SERVICE {s}:0:1:{e}:{e}:0:0:0:0:0:{u}:{n}\n".format(s=serviceType, e=epgId, u=uri, n=name)
            tvlist.append((name,service))

        tvlist = sorted(tvlist, key=lambda channel: channel[0]) # sort by name
        with open(GSBQ, "w") as f:
            f.write("#NAME GreekStreamTV\n")
            for (name, service) in tvlist:
                f.write(service)

    def update(self, answer):
        if answer:
            self.session.open(Console, _("Updating"), ["%s update" % url_sc], showStartStopText=False)

    def depends(self, answer):
        if answer:
            self.session.open(Console, _("Installing"), ["%s update" % url_pd], showStartStopText=False)

    def yellow(self):
        msg = _("Do you really want to install the necessary software dependencies?")
        self.session.openWithCallback(self.depends, MessageBox, msg, MessageBox.TYPE_YESNO)

    def blue(self):
        msg = _("For information or questions please refer to the www.satdreamgr.com forum.")
        msg += "\n\n"
        msg += _("GreekStreamTV is free.")
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def getStreams(self):
        xml = "/usr/lib/enigma2/python/Plugins/Extensions/GreekStreamTV/xml"
        list = []
        if path.isdir(xml):
            for file in listdir(xml):
                if file.endswith(".xml"):
                    list.append((path.splitext(file)[0].title().replace("_", " "), path.join(xml, file)))

        return list
