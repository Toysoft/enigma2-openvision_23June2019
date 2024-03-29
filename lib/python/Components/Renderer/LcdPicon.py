import os, re, unicodedata
from Renderer import Renderer
from enigma import ePixmap, eServiceCenter, eServiceReference, iServiceInformation
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import pathExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename
from Components.Harddisk import harddiskmanager
from ServiceReference import ServiceReference
from Components.config import config
from Components.SystemInfo import SystemInfo

searchPaths = []
lastLcdPiconPath = None

def initLcdPiconPaths():
	global searchPaths
	searchPaths = []
	for mp in ('/usr/share/enigma2/', '/'):
		onMountpointAdded(mp)
	for part in harddiskmanager.getMountedPartitions():
		onMountpointAdded(part.mountpoint)

def onMountpointAdded(mountpoint):
	global searchPaths
	try:
		if SystemInfo["PiconLCDSupport"] and not SystemInfo["grautec"] or os.path.isdir(mountpoint + 'piconlcd'):
			path = os.path.join(mountpoint, 'piconlcd') + '/'
		else:
			path = os.path.join(mountpoint, 'picon') + '/'
		if os.path.isdir(path) and path not in searchPaths:
			for fn in os.listdir(path):
				if fn.endswith('.png'):
					print "[LcdPicon] adding path:", path
					searchPaths.append(path)
					break
	except Exception, ex:
		print "[LcdPicon] Failed to investigate %s:" % mountpoint, ex

def onMountpointRemoved(mountpoint):
	global searchPaths
	if SystemInfo["PiconLCDSupport"] and not SystemInfo["grautec"] or os.path.isdir(mountpoint + 'piconlcd'):
		path = os.path.join(mountpoint, 'piconlcd') + '/'
	else:
		path = os.path.join(mountpoint, 'picon') + '/'
	try:
		searchPaths.remove(path)
		print "[LcdPicon] removed path:", path
	except:
		pass

def onPartitionChange(why, part):
	if why == 'add':
		onMountpointAdded(part.mountpoint)
	elif why == 'remove':
		onMountpointRemoved(part.mountpoint)

def findLcdPicon(serviceName):
	global lastLcdPiconPath
	if lastLcdPiconPath is not None:
		pngname = lastLcdPiconPath + serviceName + ".png"
		if pathExists(pngname):
			return pngname
	global searchPaths
	for path in searchPaths:
		if pathExists(path):
			pngname = path + serviceName + ".png"
			if pathExists(pngname):
				lastLcdPiconPath = path
				return pngname
	return ""

def getLcdPiconName(serviceName):
	service = eServiceReference(serviceRef)
	if service.getPath().startswith("/") and serviceRef.startswith("1:"):
		info = eServiceCenter.getInstance().info(eServiceReference(serviceRef))
		refstr = info and info.getInfoString(service, iServiceInformation.sServiceref)
		serviceRef = refstr and eServiceReference(refstr).toCompareString()
	#remove the path and name fields, and replace ':' by '_'
	fields = GetWithAlternative(serviceRef).split(':', 10)[:10]
	if not fields or len(fields) < 10:
		return ""
	pngname = findLcdPicon('_'.join(fields))
	if not pngname and not fields[6].endswith("0000"):
		#remove "sub-network" from namespace
		fields[6] = fields[6][:-4] + "0000"
		pngname = findLcdPicon('_'.join(fields))
	if not pngname and fields[0] != '1':
		#fallback to 1 for IPTV streams
		fields[0] = '1'
		pngname = findLcdPicon('_'.join(fields))
	if not pngname and fields[2] != '2':
		#fallback to 1 for TV services with non-standard service types
		fields[2] = '1'
		pngname = findLcdPicon('_'.join(fields))
	if not pngname: # picon by channel name
		name = ServiceReference(serviceRef).getServiceName()
		name = unicodedata.normalize('NFKD', unicode(name, 'utf_8', errors='ignore')).encode('ASCII', 'ignore')
		name = re.sub('[^a-z0-9]', '', name.replace('&', 'and').replace('+', 'plus').replace('*', 'star').lower())
		if name:
			pngname = findLcdPicon(name)
			if not pngname and len(name) > 2 and name.endswith('hd'):
				pngname = findLcdPicon(name[:-2])
			if not pngname and len(name) > 6:
				series = re.sub(r's[0-9]*e[0-9]*$', '', name)
				pngname = findLcdPicon(series)
	return pngname

class LcdPicon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = ""
		self.lastPath = None
		pngname = findLcdPicon("picon_default")
		if SystemInfo["PiconLCDSupport"] and not SystemInfo["grautec"] or os.path.isdir(mountpoint + 'piconlcd'):
			pngname = findLcdPicon("lcd_picon_default")
		else:
			pngname = findLcdPicon("picon_default")
		self.defaultpngname = None
		self.showPicon = True
		if not pngname:
			if SystemInfo["PiconLCDSupport"] and not SystemInfo["grautec"] or os.path.isdir(mountpoint + 'piconlcd'):
				tmp = resolveFilename(SCOPE_CURRENT_SKIN, "lcd_picon_default.png")
			else:
				tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
			if pathExists(tmp):
				pngname = tmp
			else:
				if SystemInfo["PiconLCDSupport"] and not SystemInfo["grautec"] or os.path.isdir(mountpoint + 'piconlcd'):
					pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/lcd_picon_default.png")
				else:
					pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
		if os.path.getsize(pngname):
			self.defaultpngname = pngname

	def addPath(self, value):
		if pathExists(value):
			global searchPaths
			if not value.endswith('/'):
				value += '/'
			if value not in searchPaths:
				searchPaths.append(value)

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.addPath(value)
				attribs.remove((attrib,value))
			elif attrib == "isFrontDisplayPicon":
				self.showPicon = value == "0"
				attribs.remove((attrib,value))
		self.skinAttributes = attribs
		self.changed((self.CHANGED_ALL,))
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			if self.showPicon or config.usage.show_picon_in_display.value:
				pngname = ""
				if what[0] != self.CHANGED_CLEAR:
					pngname = getLcdPiconName(self.source.text)
				if not pngname: # no picon for service found
					pngname = self.defaultpngname
				if self.pngname != pngname:
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
					else:
						self.instance.hide()
					self.pngname = pngname
			elif self.visible:
				self.instance.hide()

harddiskmanager.on_partition_list_change.append(onPartitionChange)
initLcdPiconPaths()
