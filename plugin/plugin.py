from os import path, listdir

from . import _
from Plugins.Plugin import PluginDescriptor
from Components.MenuList import MenuList
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.Console import Console
from Tools.Directories import resolveFilename, SCOPE_PLUGINS


GSXML = resolveFilename(SCOPE_PLUGINS, "Extensions/GreekStreamTV/stream.xml")
GSBQ = "/etc/enigma2/userbouquet.greekstreamtv.tv"


def main(session, **kwargs):
    session.open(GSMenu)


def Plugins(**kwargs):
    return PluginDescriptor(
        name=_("GreekStreamTV"),
        where=[PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_PLUGINMENU],
        description=_("Watch live stream TV"),
        icon="plugin.png",
        fnc=main)


class GSMenu(Screen):

    skin = """
        <screen name="GSMenu" position="center,center" size="3*e/4,3*e/4" title="GreekStreamTV">
            <widget name="menu" position="0,10" size="e,e-60" itemHeight="40" font="Body" textOffset="10,0" scrollbarMode="showOnDemand"/>
            <ePixmap pixmap="buttons/key_red.png" position="0,e-40" size="40,40" alphatest="blend"/>
            <ePixmap pixmap="buttons/key_green.png" position="e/4,e-40" size="40,40" alphatest="blend"/>
            <ePixmap pixmap="buttons/key_yellow.png" position="e/2,e-40" size="40,40" alphatest="blend"/>
            <ePixmap pixmap="buttons/key_blue.png" position="3*e/4,e-40" size="40,40" alphatest="blend"/>
            <widget source="key_red" render="Label" position="40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
            <widget source="key_green" render="Label" position="e/4+40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
            <widget source="key_yellow" render="Label" position="e/2+40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
            <widget source="key_blue" render="Label" position="3*e/4+40,e-40" size="e/4-40,40" font="Regular;20" valign="center"/>
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(_("GreekStreamTV"))

        self["key_red"] = StaticText(_("Close"))
        self["key_green"] = StaticText(_("Select"))
        self["key_yellow"] = StaticText(_("Update stations"))
        self["key_blue"] = StaticText(_("About"))

        menu = []
        menu.append((_("GreekStreamTV"), GSXML))
        menu.extend(self.getStreams())
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

    def yellow(self):
        def updateCb(answer):
            if answer is True:
                cmd = "{0}/update.sh {0}".format(resolveFilename(SCOPE_PLUGINS, "Extensions/GreekStreamTV"))
                self.session.open(Console, _("Updating stations"), [cmd], showStartStopText=False)
        msg = _("Do you really want to update the list of stations?")
        self.session.openWithCallback(updateCb, MessageBox, msg, MessageBox.TYPE_YESNO)

    def blue(self):
        msg = _("For information or questions please refer to the www.satdreamgr.com forum.")
        msg += "\n\n"
        msg += _("GreekStreamTV is free.")
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def getStreams(self):
        xml = resolveFilename(SCOPE_PLUGINS, "Extensions/GreekStreamTV/xml")
        list = []
        if path.isdir(xml):
            for file in listdir(xml):
                if file.endswith(".xml"):
                    list.append((path.splitext(file)[0].title().replace("_", " "), path.join(xml, file)))

        return list
