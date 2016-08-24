#!/usr/bin/env python

import bplist_parse
import network_classes

SECURITY = {1:'OPN',4:'WPA2',3:'WPA',15:'Yes'}
MODE = {0:'Infrastructure',1:'Ad-Hoc'}

class location(object):
    
    def __init__(self, **kwargs):
        """location object constructor
        
        KWARGS:
            vertical_accuracy   [int|float] location accuracy in meters
            horizontal_accuracy [int|float] (see vertical_accuracy)
            timestamp           [float|datetime] time when recorded
            altitude            [int|float] altitude in meters
            longitude           [float|longitude] ... 
            latitude            [float|latitude] ...
            course              [int|float] ????
            speed               [int|float] estimated speed when recorded
        """
        v_a = kwargs.get('vertical_accuracy')
        h_a = kwargs.get('horizontal_accuracy')
        tmstmp = kwargs.get('timestamp')
        alt = kwargs.get('altitude')
        lon = kwargs.get('longitude')
        lat = kwargs.get('latitude')
        crs = kwargs.get('course')
        spd = kwargs.get('speed')
        self.vertical_accuracy = abs(float(v_a)) if isinstance(v_a,(int,float)) else None
        self.horizontal_accuracy = abs(float(h_a)) if isinstance(h_a,(int,float)) else None
        self.timestamp = bplist_parse.BPList.date_parser(tmstmp) if type(tmstmp).__name__ in ['datetime','float'] else None
        self.altitude = float(alt) if isinstance(alt,(int,float)) else None
        self.longitude = longitude(lon) if isinstance(lon,(float,longitude)) else None
        self.latitude  = latitude(lat) if isinstance(lat,(float,latitude)) else None
        self.course = float(crs) if isinstance(crs,(int,float)) else None
        self.speed = float(spd) if isinstance(spd,(int,float)) else None
        

class coord_BASE(object):
    __slots__ = ('value',)
    def __init__(self, value):
        if isinstance(value,coord_BASE):
            value = float(value)
        if isinstance(value,basestring):
            
            value = value.replace('\xc2\xb0',' ').replace('\xb0',' ').replace("'",' ').replace('"',' ')
            value = value.split()
            if len(value)<4:
                raise ValueError, "if a string is passed to the latitude/longitude constructor, it must have the full xx\xc2\xb0xx'xx.x\"X or xx xx'xx\"X format."
            i,j,k = float(value[0]),float(value[1]),float(value[2])
            X = value[3]
            if X[0].lower() not in 'nesw': raise ValueError, "{!r} is not a valid lat/long orientation. Should be N, S, E, or W.".format(X[0])
            X = X[0]
            value = i,j,k,X
        if isinstance(value,tuple):
            if len(value)<3: raise ValueError, "if a tuple is passed to the latitude/longitude constructor, it must be at least length 3."
            sgn = 1
            if value[0] < 0:
                sgn = -1
            elif len(value)>=4 and isinstance(value,basestring):
                if value[3][0].lower() in 'sw':
                    sgn = -1
            value = round(sgn*(int(value[0])+int(value[1])/60.0+value[2]/3600.0),8)
        self.value = value
    def __setattr__(s,a,v):
        if a in s.__slots__ or a in dir(s):
            try:
                _ = getattr(s,a)
            except AttributeError:
                object.__setattr__(s,a,v)
                return
            raise TypeError, "attribute {!r} of {} object is already set".format(a,s.__class__.__name__)
        raise AttributeError, "{} object has no attribute {!r}".format(s.__class__.__name__,a)
    @property
    def letter(self):
        return ''
    @property
    def DMS_tuple(self):
        val = abs(self.value)
        deg,rem = divmod(val,1)
        min,sec = divmod(rem*60,1)
        return (int(deg), int(min), int(sec*600)/10.0)
    def __repr__(self):
        return u"{}\u00B0{}'{}\"{}".format(*(self.DMS_tuple+(self.letter,))).encode('UTF8')
    def __str__(self):
        return repr(self).replace('\xc2\xb0',' ')
    def __unicode__(self):
        return self.__repr__().decode('utf8')
    def __int__(self):
        return int(self.value)
    def __float__(self):
        return float(self.value)

class latitude(coord_BASE):
    @property
    def letter(self):
        return 'SN'[bool(self.value >= 0)]
class longitude(coord_BASE):
    @property
    def letter(self):
        return 'WE'[bool(self.value >= 0)]

class AccessPointScan(object):
    def __init__(self,dataholder,kwargs):
        get = lambda a: kwargs[a] if a in kwargs.value.keys() else None
        getv = lambda a: kwargs[a].value if a in kwargs.value.keys() else None
        bssid = get('bssid')
        if isinstance(bssid,bplist_parse.bpl_UID):
            bssid = dataholder[bssid]
        elif bssid is not None:
            bssid = bssid.value
        else:
            bssid = None
        self.bssid = network_classes.mac_addr(bssid) if bssid is not None else bssid
        self.channel = getv('channel')
        self.course = getv('course')
        firstseen,lastseen = getv('firstseen'),getv('lastseen')
        if firstseen is not None:
            firstseen = bplist_parse.BPList.date_parser(firstseen)
        if lastseen is not None:
            lastseen = bplist_parse.BPList.date_parser(lastseen)
        self.firstseen,self.lastseen = firstseen,lastseen
        locdict = getv('locationdictionary')
        locdict = dataholder[locdict] if isinstance(locdict,int) else locdict
        if not isinstance(locdict,dict):
            locdict = {}
        self.location = location(**locdict)
        self.maxrssi = getv('maxrssi')
        maxrssitime = getv('maxrssitime')
        self.maxrssitime = dataholder[maxrssitime] if isinstance(maxrssitime,int) else maxrssitime
        self.minrssi = getv('minrssi')
        self.security = SECURITY.get(getv('security'),'???({})'.format(getv('security')))
        self.speed = getv('speed')
        ssid = getv('ssid')
        self.ssid = dataholder[ssid] if isinstance(ssid,int) else ssid
        self.type = MODE.get(getv('type'),'???({})'.format(getv('type')))
        self.rates = getv('rates')
        #self.allargs = kwargs
    
    def csv_tuple(self):
        #bssid,ssid,firstseen,lastseen,channel,security,minrssi,maxrssi,latitude,longitude,altitude
        val = []
        for nem in ['bssid','ssid','firstseen','lastseen','channel','security',
                    'minrssi','maxrssi']:
            v = getattr(self,nem)
            val.append(unicode(v) if v is not None else '')
        for nem in ['latitude','longitude','altitude']:
            v = getattr(self.location,nem)
            val.append(unicode(v) if v is not None else '')
        return tuple(val)

class _dataholder(object):
    
    def __init__(self, array):
        if isinstance(array, bplist_parse.bpl_BASE):
            array = array.value
        self._array = array
        self._known_classes = {}
        self._known_values = {}
    
    
    def __getitem__(self, key):
        retraw = False
        if isinstance(key,tuple):
            if len(key) < 2:   key = key[0]
            else:   key,retraw = key[0],True
        
        if isinstance(key,bplist_parse.bpl_UID):
            key = key.value
        if not isinstance(key,int):
            raise TypeError, "_dataholder keys must be ints or UIDs, not {!r}".format(key.__class__.__name__)
        if not 0<=key<len(self._array):
            raise IndexError, "_dataholder index out of range"
        
        if key in self._known_classes:
            return self._known_classes[key]
        if key in self._known_values:
            return self._known_values[key]
        
        val = self._array[key]
        if isinstance(val,bplist_parse.bpl_Dict):
            if '$classname' in val.value.keys():
                if key not in self._known_classes:
                    self._known_classes[key] = val['$classname'].value
                return self._known_classes[key]
            
            if '$class' in val.value.keys():
                cls_idx = val['$class'].value
                
                if cls_idx not in self._known_classes:
                    _ = self[cls_idx]
                cls = self._known_classes[cls_idx]
                
                if cls == 'NSMutableDictionary':
                    madict = {}
                    
                    for itr in xrange(len(val['NS.keys'].value)):
                        k = val['NS.keys'].value[itr].value
                        v = val['NS.objects'].value[itr].value
                        
                        k, v = self[k], self[v]
                        madict[k] = v
                    self._known_values[key] = madict
                    return madict
                
                if cls == 'NSDate':
                    v = val['NS.time'].value
                    v = bplist_parse.BPList.date_parser(v)
                    self._known_values[key] = v
                    return v
                
                if cls == 'AccessPointScan':
                    v = AccessPointScan(self,val)
                    self._known_values[key] = v
                    return v
                
                if cls == 'NSMutableArray':
                    malist = []
                    
                    for v in val['NS.objects'].value:
                        malist.append(self[v])
                    self._known_values[key] = malist
                    return malist
                
                raise RuntimeError, "Unknown $class value {!r}".format(cls)
        
        v = val.value
        self._known_values[key] = v
        return v

class Wfff_log(object):
    
    __slots__ = ('_Wfff_log__dollHairSign','DATA','root')
    
    def __init__(self, fileOrPathOrBPList):
        
        __BPL = None
        
        if isinstance(fileOrPathOrBPList,bplist_parse.BPList):
            __BPL = fileOrPathOrBPList
        else:
            fileOrPath = fileOrPathOrBPList
            if isinstance(fileOrPath,kml_log):
                __BPL = fileOrPath
            elif isinstance(fileOrPath,(basestring,file)):
                if isinstance(fileOrPath,basestring):
                    fileOrPath = open(fileOrPath)
                fileOrPath.seek(0)
                mgic = fileOrPath.read(8)
                fileOrPath.seek(0)
                if mgic.lower().startswith('bplist'):
                    __BPL = bplist_parse.BPList(fileOrPath)
                elif 'xml' in mgic.lower():
                    __BPL = kml_log(fileOrPath)
                else:
                    raise ValueError, "Failed to determine filetype."
            else:
                raise TypeError, "Argument to Wfff_log constructor should be a filepath, fileobject, BPList, or kml_log, not {!r}".format(fileOrPathOrBPList.__class__.__name__)
        
        if isinstance(__BPL,bplist_parse.BPList):
            topObj = __BPL.object_table[0]
            
            self.__dollHairSign = (topObj['$archiver'].value,topObj['$version'].value, \
                                    topObj['$top']['root'].value)
            
            self.DATA = _dataholder(topObj['$objects'].value)
            
            self.root = self.DATA[self.__dollHairSign[2]]
        
        else:
            
            self.__dollHairSign = ('kml',200000,None)
            self.DATA = __BPL
            self.root = self.DATA._data
    
    @property
    def archiver(self):
        return self.__dollHairSign[0]
    @property
    def version(self):
        return self.__dollHairSign[1]
    
    def __len__(s):
        return len(self.root)
    
    def __getitem__(s,a):
        return s.root.__getitem__(a)
    
    
    def csv_iter(self,delim=u'\t',onlyheader=False):
        itr8r = self.__csv_iterator(delim)
        if onlyheader:
            return itr8r.next()
        else:
            return itr8r
    
    def __csv_iterator(self,delim):
        hdr=(u'bssid',u'ssid',u'firstseen',u'lastseen',u'channel',u'security',
             u'minrssi',u'maxrssi',u'latitude',u'longitude',u'altitude')
        yield delim.join(hdr)
        for i in self.root:
            yield delim.join(i.csv_tuple())
    
    def __setattr__(self,attr,value):
        try:
            _ = getattr(self,attr)
        except AttributeError:
            object.__setattr__(self,attr,value)
            return
        raise TypeError, "attribute {!r} is already set".format(attr)

class kml_holder_obj:
    def __init__(self,value):
        self.value = value
    def __getattr__(self,attr):
        if hasattr(self.value, attr):
            return getattr(self.value,attr)
    def __dir__(self):
        lst = ['value']
        return lst + dir(self.value)

class kml_log(object):
    def __init__(self, fileOrPath):
        
        if isinstance(fileOrPath,basestring):
            if not os.path.isfile(fileOrPath):
                raise ValueError, "Failed to find file."
            fileOrPath = open(fileOrPath)
            
        if not isinstance(fileOrPath,file):
            raise TypeError, "kml_log constructor takes a filepath or a fileobject, not a {!r}.".format(fileOrPath.__class__.__name__)
        
        from sys import modules
        bs_ = None
        if 'BeautifulSoup' in modules:
            bs_ = modules['BeautifulSoup']
        elif 'bs4' in modules:
            bs_ = modules['bs4']
        else:
            try:
                import bs4
            except ImportError:
                try:
                    import BeautifulSoup
                except ImportError:
                    raise ImportError, "Failed to load BeautifulSoup module."
                else:
                    bs_ = BeautifulSoup
            else:
                bs_ = bs4
        self.bs_ = bs_
        self.prepare_soup()
        
        self.soup = self.bs_.BeautifulSoup(fileOrPath)
        
        self._data = []
        
        self.consume_soup()
        
        del self.soup
        self._data = tuple(self._data)
        
    
    def __getitem__(self,itm):
        self._data.__getitem__(itm)
    
    def prepare_soup(self):
        if not hasattr(self,'bs_'):
            raise RuntimeError, "'bs_' attribute not yet set"
        method_changes = {'renderContents':'encode_contents','replaceWith':\
                'replace_with','replaceWithChildren':'unwrap','findAll':\
                'find_all','findAllNext':'find_all_next','findAllPrevious':\
                'find_all_previous','findNext':'find_next','findNextSibling':\
                'find_next_sibling','findNextSiblings':'find_next_siblings',\
                'findParent':'find_parent','findParents':'find_parents',\
                'findPrevious':'find_previous','findPreviousSibling':\
                'find_previous_sibling','findPreviousSiblings':\
                'find_previous_siblings','nextSibling':'next_sibling',\
                'previousSibling':'previous_sibling'}
        cls = self.bs_.Tag
        fixed_list = []
        for old,new in method_changes.items():
            if not hasattr(cls,new) and hasattr(cls,old):
                fixed_list.append(old)
                setattr(cls,new,getattr(cls,old))
        cls = self.bs_.PageElement
        for old,new in method_changes.items():
            if old not in fixed_list and not hasattr(cls,new) and hasattr(cls,old):
                fixed_list.append(old)
                setattr(cls,new,getattr(cls,old))
    
    def placemark_handler(self,placemark,name):
        obj = None
        if name == 'name':
            obj = placemark.find('name',recursive=False)
        elif name == 'point':
            obj = placemark.find('point',recursive=False)
            if obj:
                obj = obj.coordinates
        else:
            xtended = placemark.find('extendeddata',recursive=False)
            if not xtended:
                return None
            obj = xtended.find(attrs={'name':name})
            if not obj:
                return None
            obj = obj.value
        
        if obj is not None:
            val = unicode(obj.string).strip()
            if val.startswith('<![CDATA[') and val.endswith(']]>'):
                val = val[9:-3]
            return val
    
    def consume_soup(self):
        document = self.soup.find('document')
        if not document:
            raise ValueError, "Failed to find 'document' element"
        folder = document.find('folder',recursive=False)
        placemarks = folder.find_all('placemark',recursive=False)
        
        for AP in placemarks:
            AP_dict = kml_holder_obj({})
            
            ssid = self.placemark_handler(AP,'name')
            AP_dict['ssid'] = kml_holder_obj(ssid)
            
            bssid = self.placemark_handler(AP,'BSSID')
            if bssid:
                bssid = tuple(bssid[i:i+2] for i in range(0,len(bssid),2))
            AP_dict['bssid'] = kml_holder_obj(bssid)
            
            mode = self.placemark_handler(AP,"Mode")
            if mode and 'structure' in mode.lower():
                mode = 0
            elif mode and 'hoc' in mode.lower():
                mode = 1
            AP_dict['type'] = kml_holder_obj(mode)
            
            security = self.placemark_handler(AP,"Secure")
            if security and 'yes' in security.lower():
                security = 15
            elif security and 'no' in security.lower():
                security = 1
            elif security and security.isdigit():
                security = int(security)
            AP_dict['security'] = kml_holder_obj(security)
            
            location_dict = kml_holder_obj({})
            
            #ints:
            for name,dval in [('RSSI','minrssi'),('RSSI','maxrssi'),\
                        ('Channel','channel'),('Accuracy','vertical_accuracy'),\
                        ('Accuracy','horizontal_accuracy'),('Altitude','altitude')]:
                kml_val = self.placemark_handler(AP,name)
                if kml_val is not None:
                    try:
                        kml_val = int(kml_val)
                    except:
                        kml_val = None
                if name in ['RSSI','Channel']:
                    AP_dict[dval] = kml_holder_obj(kml_val)
                else:
                    location_dict[dval] = kml_val
            
            #floats:
            for name,dval in [('Speed','speed'),('Course','course')]:
                kml_val = self.placemark_handler(AP,name)
                if kml_val is not None:
                    try:
                        kml_val = float(kml_val)
                    except:
                        kml_val = None
                AP_dict[dval] = kml_holder_obj(kml_val)
            
            location = self.placemark_handler(AP,'Location')
            if location:
                location = location.split(', ')
                lon,lat = None,None
                if len(location) > 2:
                    if location[2].isdigit():
                        location = location[:2]
                if len(location) >= 2:
                    if '-' in location[0]:
                        lon = location[0].strip()
                        lat = location[1].strip()
                    else:
                        lon = location[1].strip()
                        lat = location[0].strip()
                try:
                    location_dict['longitude'] = float(lon)
                except: pass
                try:
                    location_dict['latitude'] = float(lat)
                except: pass
            taim = self.placemark_handler(AP,'Location Time')
            if not taim:
                taim = self.placemark_handler(AP,'Device Time')
            if taim is not None:
                from datetime import datetime
                try:
                    taim = datetime.strptime(taim,"%d %b %Y %H:%M:%S")
                except Exception as e:
                    print e
                    try:
                        taim = datetime.strptime(taim,"%d %B %Y %H:%M:%S")
                    except Exception as e:
                        print e
                        taim = None
            if taim:
                AP_dict['lastseen'] = kml_holder_obj(taim)
                location_dict['timestamp'] = taim
            
            rates = self.placemark_handler(AP,'Rates')
            if rates is not None:
                ratelist = rates.split(', ')
                rates = []
                for i in ratelist:
                    i = i.strip().strip(',')
                    if i.isdigit():
                        rates.append(int(i))
                rates = tuple(rates)
                AP_dict['rates'] = kml_holder_obj(rates)
            
            AP_dict['locationdictionary'] = location_dict
            
            generatedAP = AccessPointScan(self,AP_dict)
            
            self._data.append(generatedAP)

if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Convert WiFiFoFum logs to "\
                        "usable formats")
    parser.add_argument('wfff_file',type=argparse.FileType('r'),metavar='LOGFILE',
                        help="the Wfff file to parse")
    arg_format = parser.add_argument('-f','--format',choices=['csv'],help="format for output")
    arg_output = parser.add_argument('-o','--output',help="file to write to")
    parser.add_argument('--check',action='store_true',help="other options will"\
                        "be ignored and the file will be checked for parsability."\
                        " 'success' or 'failure' will be printed, and the "\
                        "status code will be 0 or 1 for success or failure respectively.")
    parser.add_argument('-d','--delimiter',metavar='X',default='tab',help="delimiter"\
                        " for the `-f csv` option. Value can be 'tab' or any single"\
                        " ASCII or unicode character. [WARNING: it is recommended"\
                        " to choose a character that is not likely in the output]")
                        
    
    args = parser.parse_args()
    
    
    if args.check:
        try:
            fl = Wfff_log(args.wfff_file)
        except:
            print "failure"
            sys.exit(1)
        print "success"
        sys.exit(0)
    
    else:
        if not args.output:
            raise argparse.ArgumentError(arg_output,"no output argument provided")
        if not args.format:
            raise argparse.ArgumentError(arg_format,"no format argument provided")
        if args.format == 'csv':
            if args.delimiter == 'tab':
                args.delimiter = u'\t'
            else:
                args.delimiter = args.delimiter.decode('utf8')
        
        ofile = open(args.output,'w')
        
        wfff = Wfff_log(args.wfff_file)
        
        for line in wfff.csv_iter(args.delimiter):
            ofile.write((line+u'\n').encode('utf8'))
        ofile.flush()
        ofile.close()
        sys.exit(0)
