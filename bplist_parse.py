#!/usr/bin/env python

import os,struct,collections

VERBOSE = False

def LOG(arg,**kwargs):
    if VERBOSE:
        if kwargs.get('repr',kwargs.get('!r')):
            print "##LOG:  {!r}".format(arg)
        else:
            print "##LOG:  {}".format(arg)


kCFMarker = collections.namedtuple('kCFMarker',('Null','False','True','URL',\
                                                'BasedURL','UUID','Fill',\
                                                'Int','Real','Date','Data',\
                                                'ASCIIString','Unicode16String',\
                                                'Unicode8String','UID',\
                                                'Array','OrdSet','Set','Dict'))\
                (Null=0x00,False=0x08,True=0x09,URL=0x0C,BasedURL=0x0D,UUID=0x0E,\
                 Fill=0x0F,Int=0x10,Real=0x20,Date=0x33,Data=0x40,ASCIIString=0x50, \
                 Unicode16String=0x60,Unicode8String=0x70,UID=0x80, Array=0xA0, \
                 OrdSet=0xB0,Set=0xC0,Dict=0xD0)


def marker_to_type(mrkr):
    try:
        idx = kCFMarker.index(mrkr)
        return kCFMarker._fields[idx]
    except:
        return None

BPL_trailer = collections.namedtuple('BPL_trailer',('sortVersion','offsetIntSize','objectRefSize','numObjects','topObject','offsetTableOffset'))
BPL_indices = collections.namedtuple('BPL_indices',('header','objectTable','offsetTable','trailer','EOF'))

class BPLError(RuntimeError): # < RuntimeError < StandardError < Exception
    pass

class BPLSyntaxError(BPLError):
    pass

class BPLValueError(BPLError,ValueError):
    def __init__(self,value,reason='',val_idx=-1,fname=None):
        """Based on arguments provided, the following are output combos:
            
            ``Object value '$VALUE' ['$FNAME' ][$IDX ]is invalid( : $REASON | '.').``
            """
        self.reason = ": {}".format(reason) if reason else "."
        self.val_idx = val_idx if (isinstance(val_idx,int) and val_idx>=0) \
                                else None
        self.fname = fname if isinstance(fname,basestring) else None
        self.value = value
    
    def __str__(self):
        ret = "Object value {!r} ".format(self.value)
        if self.fname:
            ret += "in file {!r} ".format(self.fname)
        if self.val_idx:
            ret += "at index {} ".format(self.val_idx)
        ret+= "is invalid{}".format(self.reason)
        return ret


#class offset_table(tuple):
#    
#    def __new__(cls,bplist):
#        if not isinstance(bplist,BPList):
#            raise TypeError, "'bplist' argument of offset_table constructor should be a BPList."
#        
#        offsetTable = bplist._raw_file[ bplist.indices.offsetTable:bplist.indices.trailer ]
#        intSize = bplist.offsetIntSize
#        cnt,rmndr = divmod( len(offsetTable) , intSize )
#        
#        if rmndr != 0:
#            print "WARNING: length of offsetTable divided by the size of offsetInts has a remainder of {}.".format(rmndr)
#        if cnt != bplist.numObjects:
#            print "WARNING: Calculated number of offsets in offsetTable ({}) is different than numObjects ({}) from trailer.".format(cnt,self.bplist.numObjects)
#        fmt = '!' +'xBHxIxxxQ'[intSize]*cnt
#        
#        theval = struct.unpack(fmt, offsetTable)
#        first_idx = bplist.trailer.topObject
#        
#        return super(offset_table, cls).__new__(cls, (first_idx, theval))
#    
#    @property
#    def _astuple(s):
#        return tuple.__getitem__(s,1)
#    
#    @property
#    def index_offset(s):
#        return tuple.__getitem__(s,0)
#    
#    def __getitem__(realself, key):
#        if isinstance(key,int):
#            key += realself.index_offset
#        return self[key]
#    
#    def __getattribute__(s,a):
#        a_ = a[2:-2] if (a[:2]==a[-2:]=='__') else None
#        if a in ['_astuple','index_offset','index'] or (a_ and a_ in \
#                    ['class','delattr','doc','getitem','getslice',\
#                     'hash','init','repr','setattr','sizeof'] \
#                     or a not in dict(tuple):
#            #these are attributes NOT to pass to the inner tuple
#            return tuple.__getattribute__(s,a)
#        return tuple.__getitem__(s,1).__getattribute__(a)

class bpl_BASE:
    __dirs__ = {'__class__','__doc__','__init__','__int__','__hash__','__module__','__repr__','value','value_type','refnum','is_same_as'}
    __cmps__ = {'lt','le','eq','ne','gt','ge','cmp'}
    def __init__(self,val,refnum,objTable_parent):
        #if not marker_to_type(obj_type):
        #    if not isinstance(obj_type,int):
        #        raise TypeError, "'obj_type' argument for bpl_objects must be an int."
        #    if obj_type&0xF0 and obj_type&0xF0!=3:
        #        obj_type &= 0xF0
        #    if not marker_to_type(obj_type):
        #        raise ValueError, "Unknown obj_type '0x{:02X}'".format(obj_type)
        #self.__obj_type = obj_type
        self._props_ = (val,int(refnum),objTable_parent)
    @property
    def value(s):
        return s._props_[0]
    @property
    def value_type(s):
        return type(s._props_[0])
    @property
    def refnum(s):
        return s._props_[1]
    def __int__(s):
        return s._props_[1]
    def __hash__(s):
        return hash(s.refnum)
    def __dir__(s):
        return list(s.__dirs__ | bpl_BASE.__dirs__ | s.__cmps__ | bpl_BASE.__cmps__)
    def __repr__(s):
        objtyp = s.__class__.__name__[4:]
        return "<bplist {} object: {!r}>".format(objtyp,s.value)
    def is_same_as(s,o):
        return (s.__class__ is o.__class__ and s.value == o.value)
    def __getattr__(s,a):
        if a[:2] == a[-2:] == '__' and a[2:-2] in (s.__cmps__ | bpl_BASE.__cmps__):
            return getattr(s._props_[0],a)
        raise AttributeError, "{} instance has no attribute {!r}".format(s.__class__.__name__,a)
    def __setattr__(s,a,v):
        if a == '_props_':
            try: _ = s._props_
            except AttributeError:
                s.__dict__['_props_'] = v
                return
        elif a in dir(s):
            raise AttributeError, "attribute {!r} of bpl_* instances is not writable.".format(a)
        raise AttributeError, "{} instance has no attribute {!r}".format(s.__class__.__name__,a)

class bpl_Null(bpl_BASE):   pass
class bpl_False(bpl_BASE):  pass
class bpl_True(bpl_BASE):   pass
class bpl_URL(bpl_BASE):    pass
class bpl_BasedURL(bpl_BASE):pass
class bpl_UUID(bpl_BASE):   pass
class bpl_Int(bpl_BASE):    pass
class bpl_Real(bpl_BASE):   pass
class bpl_Date(bpl_BASE):   pass
class bpl_Data(bpl_BASE):   pass
class bpl_ASCIIString(bpl_BASE):    pass
class bpl_Unicode16String(bpl_BASE):pass
class bpl_Unicode8String(bpl_BASE): pass
class bpl_UID(bpl_BASE):    pass
class bpl_Array(bpl_BASE):
    __dirs__ = {'__getitem__'}
    def __getitem__(s,k):
        return s.value[k]
class bpl_OrdSet(bpl_BASE): pass
class bpl_Set(bpl_BASE):    pass
class bpl_Dict(bpl_BASE):
    __dirs__ = {'__getitem__'}
    def __getitem__(s,k):
        for i,j in s.value.items():
            if k == i:
                return j
        raise KeyError, k


def type_to_class(typ):
    clazz = globals().get('bpl_'+typ)
    if not clazz and hasattr(kCFMarker,typ):
        LOG("Globals()=\\\n{}".format(globals()))
        raise RuntimeError, "class 'bpl_{}' has disappeared from the module!".format(typ)
    return clazz


def recursive_realify(val):
    
    if not isinstance(val,bpl_BASE):
        raise TypeError, "recursive_realify() argument should be a bpl_* instance."
    ret = NotImplemented
    if isinstance(val,(bpl_Array,bpl_OrdSet,bpl_Set)):
        ret = []
        for itm in val.value:
            ret.append( recursive_realify(itm) )
        ret = val.value_type(ret)
    elif isinstance(val,bpl_Dict):
        ret = {}
        for i,j in val.value.items():
            i = recursive_realify(i)
            j = recursive_realify(j)
            ret[i] = j
    else:
        ret = val.value
    return ret


class object_table(object):
    
    #'Reference' numbers:   bplist-native indices; start at first_refnum.
    #                       Used as keys for ObjectTable
    #'Index' numbers:       0-based *positional* indices; ordinal.
    #                       Used as indices for the OffsetTable.
    #
    #Example:   Suppose first_refnum := 3, and there are 5 objects in 
    #           the table. 
    #           The reference numbers used in the ObjectTable will be
    #           (3,4,5,6,7). The OffsetTable will refer to these such
    #           that OffsetTable[0] is the offset of Reference '3',
    #           and to access the object use ObjectTable[3].
    #           In other words, OffsetTable[0] <-> ObjectTable[3]
    
    __slots__ = ('_object_table__BPL','_object_table__ObjT','_object_table__OffT','_object_table__idx0')
    
    def __init__(self,bplist):
        if not isinstance(bplist,BPList):
            raise TypeError, "'bplist' argument of object_table constructor should be a BPList."
        
        self.__BPL = bplist
        
        raw_offsetTable = bplist._raw_file[ bplist.indices.offsetTable:bplist.indices.trailer ]
        intSize = bplist.offsetIntSize
        cnt,rmndr = divmod( len(raw_offsetTable) , intSize )
        
        if rmndr != 0:
            print "WARNING: length of offsetTable divided by the size of offsetInts has a remainder of {}.".format(rmndr)
        if cnt != bplist.numObjects:
            print "WARNING: Calculated number of offsets in offsetTable ({}) is different than numObjects ({}) from trailer.".format(cnt,self.bplist.numObjects)
        fmt = '!{0}{1}'.format(cnt,'xBHxIxxxQ'[intSize])
        
        self.__OffT = struct.unpack(fmt, raw_offsetTable)
        self.__idx0 = bplist.trailer.topObject
        
        #key:=refnum-int
        #val:=bpl_%type% instance
        self.__ObjT = {}
    
    @property
    def first_refnum(s):
        return s.__idx0
    
    def _refnum_to_idx(self,refnum,expln=False):
        #takes a Reference number and (if valid) returns the
        # related Index number.
        table_sz = len(self.__OffT)
        
        if refnum < 0 and refnum+table_sz >= 0:
            refnum += table_sz
        elif self.__idx0 <= refnum < table_sz:
            refnum -= self.__idx0
        elif expln:
            if refnum < 0:
                return (None,'<<')#too negative
            elif refnum < self.__idx0:
                return (None,'<ref0')#less than 0th refnum
            else:
                return (None,'>>')#too large
        else:
            return None
        
        if expln:
            return (True,refnum)
        return refnum
    
    
    def __getitem__(self,key):
        #key should be a Reference number
        refnum = key
        if not isinstance(key,int):
            raise TypeError, "object_table indices must be integers, not {!r}.".format(key.__class__.__name__)
        
        if refnum in self.__ObjT:
            return self.__ObjT[refnum]
        #refnum not yet in ObjectTable. Verify and add it if valid
        
        OKAY,key = self._refnum_to_idx(key,True)
        #key is now an Index number
        if not OKAY:
            err = "reference number '{}' ".format(key)
            if key == '<<':
                err+="is too negative."
            elif key=='<ref0':
                err+="is less than the first reference number ({}).".format(self.__idx0)
            else:
                err+="is larger than the last reference number ({}).".format(self.__indx0+tablesz)
            raise IndexError, err
        
        
        bpl_idx = self.__OffT[key]
        
        fmt, valu, _ = self.__BPL.object_parser(bpl_idx)
        clazz = type_to_class(fmt)
        if not clazz:           #value, reason, val_idx, self.fname
            raise BPLValueError(fmt,"bad object-type returned by object_parser().",bpl_idx,self.__BPL.fname)
        if clazz is bpl_Dict:
            valu = dict(valu)
        
        inst = clazz(valu, refnum, self)
        self.__ObjT[refnum] = inst
        return inst
    
    
    def get(self,k,d=None):
        #k should be a Reference number
        try:
            return self[k]
        except LookupError:
            return d
    
    
    def __contains__(self,key):
        #key should be a Reference number
        if self._refnum_to_idx(key) is not None:
            if key not in self.__ObjT:
                _ = self[key]
            return True
        return False
    
    def _load_value(self,start,end=None,as_idx=False):
        
        if end is None:
            end = start+1
        elif end<start or (start < 0)^(end < 0):
            raise ValueError, "If 'end' argument is provided to _load_value(), 'start' must be less than 'end' and both have the same sign."
        
        max_idx = len(self.__ofsetTable)
        max_ref = max_idx + self.first_refnum
        
        start_idx,end_idx = start,end
        if as_idx:
            if start_idx < 0:
                start_idx+=max_idx
                end_idx+=max_idx
            if start_idx < 0 or start_idx >= max_idx:
                raise IndexError, "Argument(s) to _load_value are out of bounds."
            start,end = start_idx+self.first_refnum,end_idx+self.first_refnum
        else:
            OKAY, start_idx = self._refnum_to_idx(start,True)
            if not OKAY:
                raise IndexError, "Argument(s) to _load_value are out of bounds."
            end_idx = start_idx+(end-start)
        
        
        for itr in range(start,end):
            if itr in self.__ObjT:
                continue
            if itr >= max_ref:
                return
            _ = self[itr]
    
    
    def __iter__(self):
        L = 1
        for itr in xrange( len( self.__OffT ) ):#iterating thru offsetTable
            refnum_itr = itr+self.first_refnum
            if refnum_itr not in self.__ObjT:
                L+= 1 if L >= 1 else 2
                self._load_value(refnum_itr,refnum_itr+L)
            
            yield self.__ObjT[refnum_itr]

    
    def __len__(self):
        return len(self.__OffT)
    
    def find(self,obj):
        #obj should be a bpl_* instance
        #Returns the Reference number of the object *IFF* it has been loaded
        #If not found, returns None
        if not isinstance(obj,bpl_BASE):
            raise TypeError, "'obj' argument of find() must be a bpl_* instance"
        for idx in xrange( len( self.__OffT ) ):
            refnum = idx+self.first_refnum
            if obj.is_same_as(self.__ObjT[refnum]):
                return refnum
        return None
    
    @property
    def loaded_count(self):
        return len(self.__ObjT)
    @property
    def unloaded_count(self):
        return len(self.__ObjT)-len(self.__OffT)
    @property
    def loaded_ratio(self):
        return 1.0*len(self.__ObjT)/len(self.__OffT)

class CFUUID(object):
    
    __slots__ = ()
    
    def __init__(self,*args):
        val = []
        if len(args) == 2 and all(map(isinstance,args,(int,int))):
            args = [ (args[0]<<64)|args[1] ]
        
        if len(args) == 1:
            tmpval = args[0]
            if isinstance(tmpval,basestring):
                itr,realitr = 0,0
                while 1:
                    if itr in [8,13,18,23] and hx[itr] == '-':
                        tmpval = tmpval[:itr]+tmpval[itr+1:]
                        realitr+=1
                    
                    hx = tmpval[itr:itr+2].lower()
                    if len(hx) < 2:
                        if itr==32:
                            break
                        raise ValueError, "UUID of insufficient length."
                    elif itr >= 32:
                        raise ValueError, "UUID of excessive length."
                    
                    try: hx=int(hx,16)
                    except ValueError:
                        bad_chr = hx[0] if (not hx[0].isdigit() or hx[0] not in 'abcdef') else hx[1]
                        
                        raise ValueError, "Invalid UUID character {!r} at index {}.".format(bad_chr,realitr)
                    
                    val.append(hx)
                    itr+=2
                    realitr+=2
            
            elif isinstance(tmpval,int):
                for i in xrange(16):
                    val.append( tmpval&0xFF )
                    tmpval >>= 8
            
            else:
                raise TypeError, "CFUUID constructor takes 1 int/string, or 16 ints/strings, not 1 {}.".format(tmpval.__class__.__name__)
        
        elif len(args) == 16:
            typ = int
            if isinstance(args[0],basestring):
                typ = basestring
            elif not isinstance(args[0],int):
                raise TypeError, "CFUUID constructor takes 1 int/string, or 16 ints/strings; {} objects not accepted.".format(args[0].__class__.__name__)
            if not all(isinstance(a,typ) for a in args):
                raise ValueError, "Cannot mix-and-match types for CFUUID constructor."
            
            if typ is int:
                for i in args:
                    if i>0xFF:
                        raise ValueError, "CFUUID constructor was passed at least one value greater than 0xFF."
                    val.append(int(i))
            else:
                baze = 10
                if any(True for i in args if i[:2] in ('0x','0X')):
                    baze = 16
                for i in args:
                    i = int(i,baze)
                    if not 0<=i<=0xFF:
                        raise ValueError, "CFUUID constructor was passed at least one value greater than 0xFF."
                    val.append(i)
        else:
            raise ValueError, "CFUUID constructor takes 1 int/string, or 16 ints/strings."
        self.array = tuple(val)
    
    @property
    def array(self):
        i = self.__class__.prop.fset(self,hash(self))
        return i
    @array.setter
    def array(self,value,holdr={}):
        if value == hash(self):
            if value in holdr:
                return holdr[value]
            return None
        if hash(self) in holdr:
            return None
        holdr[hash(self)] = value
        return value
    
    @property
    def _asint(self,holdr={}):
        h=hash(self)
        if h not in holdr:
            v = 0
            for B in range(15,-1,-1):
                v=(v<<8)|self.array[B]
            holdr[h]=v
        return holdr[h]
    
    def __str__(self):
        RA = self.array
        return "{:02X}{:02X}{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}".format(*RA)
    __repr__ = __str__
    
    def __hex__(self):
        return ['0x{:02x}'.format(i) for i in self.array].join(', ')
    
    def __len__(s):  return 16
    def __int__(s):  return s._asint
    def __iter__(s): return iter(s.array)
    def __contains__(s,i): return bool(i in s.array)
    def __getitem__(s,k): return list(s.array)[k]


class object_reference(object):
    
    __slots__ = ('_value_tuple',)
    
    def __init__(self,refval,bpl_inst):
        self._value_tuple = (refval,bpl_inst)
    
    #TODO
    
    
    
    def __setattr__(s,a,v):
        if a in self.__slots__:
            try:
                _ = s.__getattribute__(a)
            except AttributeError:
                object.__setattr__(s,a,v)
        else:
            raise AttributeError, "{!r} object has no attribute {!r}".format(self.__class__.__name__,a)
    def __delattr__(s,a,v):
        raise AttributeError, "can't delete {!r} attribute".format(a)

class BPList(object):
    
    __slots__ = ('format_version','_raw_file','fname','indices','object_table','trailer')
    
    def __init__(self, fileOrPath):
        
        
        if isinstance(fileOrPath,basestring):
            isfl = False
            try:
                isfl = os.path.isfile(fileOrPath)
            except:
                pass
            else:
                if isfl:
                    fileOrPath = file(fileOrPath,'rb')
        
        if isinstance(fileOrPath,basestring):
            
            self._raw_file = fileOrPath
            self.fname = '<<from-string>>'
            
            del fileOrPath
        
        elif isinstance(fileOrPath,file) or hasattr(fileOrPath,'read'):
            hstr = lambda _atr,_fop=fileOrPath: hasattr(_fop,_atr)
            
            if hstr('name'):
                self.fname = fileOrPath.name if (fileOrPath.name[:1]=='<' or '/' not in fileOrPath.name) else os.path.basename(fileOrPath.name)
            else:
                self.fname = "<<from-{}-object>>".format(fileOrPath.__class__.__name__)
            
            if hstr('mode') and 'r' not in fileOrPath.mode.lower():
                raise IOError, "Could not read from file {!r}, mode is set to {!r}.".format(self.fname,fileOrPath.mode)
            
            if hstr('closed') and fileOrPath.closed:
                raise IOError, "Could not read from file {!r}, file is closed.".format(self.fname)
            
            self._raw_file = fileOrPath.read()
            
            if hstr('close'):
                fileOrPath.close()
            
            del fileOrPath
        
        
        if self._raw_file[:6] != 'bplist':
            raise BPLSyntaxError, "Invalid magic number {!r}.".format(self._raw_file[:7])
        
        self.format_version = self._raw_file[6:8]
        
        if self.format_version == '15':
            Version15Error = type('Version15Error',(Exception,), {})
            raise Version15Error, "Ah yes, 'bplist15'. This file is a "\
                                  "Binary Plist version 15, aka version"\
                                  " 1.5, aka convolution. If you know how"\
                                  " it works, let me know. In the meantime"\
                                  ", sorry."
        elif self.format_version[0] != '0':
            raise BPLSyntaxError, "Unknown version value {!r}.".format(self.format_version)
        
        self.get_trailer()
        
        self.object_table = object_table(self)
    
    @property
    def offsetIntSize(s):
        return s.trailer.offsetIntSize
    @property
    def objectRefSize(s):
        return s.trailer.objectRefSize
    @property
    def numObjects(s):
        return s.trailer.numObjects
    
    
    
    def get_trailer(self,val=None):
        try:
            return self.trailer
        except AttributeError:
            pass
        
        packfmt = '!5xBBBQQQ'
        
        if val is None:
            val = self._raw_file[-32:]
        if isinstance(val,basestring) and len(val) >= 32:
            val = val[-32:]
        else:
            raise ValueError, "get_trailer() argument should be a string of at least 32 characters."
        
        self.trailer = BPL_trailer( *struct.unpack(packfmt,val) )
        
        #indices
        i_eof = len(self._raw_file)
        i_trailer = i_eof-32
        i_offsetTable = self.trailer.offsetTableOffset
        if i_offsetTable >= i_trailer:
            raise BPLSyntaxError, "'offsetTableOffset' value (the position of the Offset Table) is outside of the file."
        
        fmt = '!' +'xBHxIxxxQ'[self.trailer.offsetIntSize]
        raw_i_oT = self._raw_file[i_offsetTable:i_offsetTable+self.trailer.offsetIntSize]
        
        i_objectTable = struct.unpack(fmt,raw_i_oT)[0]
        
        if i_objectTable%2 != 0 and i_objectTable > 8:
            #for my own sanity, i_objectTable is the first MARKER, not the first value...
            i_objectTable-=1
        
        self.indices = BPL_indices(0,i_objectTable,i_offsetTable,i_trailer,i_eof)
        
        return self.trailer
    
    
    def getbyte_int(self,marker_idx):
        return struct.unpack('!B',self._raw_file[marker_idx])[0]
    
    @staticmethod
    def date_parser(seconds):
        import datetime
        if isinstance(seconds,datetime.datetime):
            return seconds
        return datetime.datetime(2001,1,1)+datetime.timedelta(seconds=seconds)
    
    
    def variable_len_object_parser(self,mrkr,val_idx,signed=None):
        # (signed==True)  -> (force signed values)
        # (signed==False) -> (force unsigned values)
        #   (else)  -> (self-determining)
        hi_nib,lo_nib = mrkr&0xF0,mrkr&0xF
        LOG("hi_nib='{:02X}', lo_nib='{:02X}'".format(hi_nib,lo_nib))
        
        if not isinstance(signed,bool):
            signed = None
        SignedChk = lambda vvv: vvv.lower() if signed else vvv.upper() if signed==False else vvv
        
        cnt = lo_nib #bytelength of value IF normal type, ELSE item count
        if hi_nib in [kCFMarker.Int, kCFMarker.Real, kCFMarker.Date]:
            cnt = 2**lo_nib #for those types using the '2^nnnn' method
        
        elif hi_nib == kCFMarker.Null:
            cnt = 0 #once-called "Singleton" objects default to 0 length
        
        total_len = 1 #bytelength of everything; marker, length_int, value
        true_val_idx = val_idx #actual val_idx if using length_int
        
        
        #objects using int as cnt
        if lo_nib == 0xF and hi_nib&0xC0 and hi_nib&0x60:
            int_mrkr = self.getbyte_int(val_idx)
            
            if int_mrkr&0xF0 != kCFMarker.Int:
                raise BPLValueError(int_mrkr,"value's high nibble must be {}, i.e. an integer marker.".format(kCFMarker.Int>>4),val_idx,self.fname)
            
            addlen, cnt = self.variable_len_object_parser(int_mrkr,val_idx+1)
            total_len += addlen
            true_val_idx += addlen
        
        bytlen = cnt #actual bytelength of value (doesn't include length_int)
        
        #objref users (array,set,dict,etc...)
        if hi_nib in [kCFMarker.Array,kCFMarker.OrdSet,kCFMarker.Set,kCFMarker.Dict]:
            bytlen = self.objectRefSize * cnt
            
            if hi_nib == kCFMarker.Dict:
                bytlen *= 2
        
        if hi_nib == kCFMarker.UID:
            cnt = lo_nib+1
            bytlen = cnt
            
            
        elif hi_nib == kCFMarker.Unicode16String:
            bytlen *= 2
        
        total_len += bytlen
        #               #
        # VALUE PARSING #
        #               #
        val = self._raw_file[true_val_idx:true_val_idx+bytlen]
        objref_fmt = 'BBHHIIIIQ'[self.objectRefSize]
        
        badmarkererr = BPLValueError(hex(mrkr),"unexpected marker value.",val_idx-1, self.fname)
        
        LOG("val={!r}, cnt={}, bytlen={}".format(val,cnt,bytlen))
        
        if hi_nib in [kCFMarker.ASCIIString, kCFMarker.Unicode16String, kCFMarker.Unicode8String]:
            
            #Unicode16String: 0x60
            if hi_nib == kCFMarker.Unicode16String:
                val = val.decode('UTF-16BE')
            
            #Unicode8String: 0x70
            elif hi_nib == kCFMarker.Unicode8String:
                val = val.decode('UTF-8')
            
            #ASCIIString: 0x50
            else:
                val = val.decode('ASCII')
        
        #Data: 0x40
        elif hi_nib == kCFMarker.Data:
            
            val = bytearray(val)
        
        #Array,OrdSet,Set: 0xA0,0xB0,0xC0
        elif hi_nib in [kCFMarker.Array,kCFMarker.OrdSet,kCFMarker.Set]:
            
            fmt = "!{}{}".format(cnt,objref_fmt)
            LOG("unpacking: fmt={!r}, val={!r}".format(fmt,val))
            val = list( struct.unpack(fmt,val) )
        
        #Dict: 0xD0
        elif hi_nib == kCFMarker.Dict:
            
            fmt = "!{}{}".format(cnt,objref_fmt)
            
            LOG("unpacking: fmt={!r}, val={!r}".format(fmt,val[:bytlen/2]))
            kees = struct.unpack(fmt,val[:bytlen/2])
            LOG("unpacking: fmt={!r}, val={!r}".format(fmt,val[bytlen/2:]))
            vals = struct.unpack(fmt,val[bytlen/2:])
            
            val = [ (kees[i],vals[i]) for i in xrange(cnt) ]
        
        #UID: 0x80
        elif hi_nib == kCFMarker.UID:
            
            if cnt not in [0,1,2,4,8,16]:
                raise BPLValueError(cnt,"value must be a power of 2.",val_idx-1,self.fname) 
            
            if cnt == 16:
                v2,v1 = struct.unpack('!QQ',val)
                val = (v2<<(64))|v1
            else:                   
                fmt = "!{}".format('xBHxIxxxQ'[cnt])
                val = struct.unpack(fmt,val)[0]
        
        #Int: 0x10
        elif hi_nib == kCFMarker.Int:
            
            if cnt == 16:
                #no evidence that non-'00' formats use unsigned 16B ints
                v2,v1 = struct.unpack(SignedChk('!qq'), val)
                val = (v2<<(64))|(v1&0xFFFFFFFFFFFFFFFF)
            
            elif cnt == 8:
                #no evidence that non-'00' formats use unsigned 8B ints
                val = struct.unpack(SignedChk('!q'),val)[0]
            
            else:
                #no evidence that non-'00' formats use signed 4, 2, or 1B ints
                fmt = SignedChk( '!{}'.format('xBHHI'[cnt]) )
                val = struct.unpack(fmt,val)[0]
        
        #Real: 0x20
        elif hi_nib == kCFMarker.Real:
            
            fmt = '!f' if cnt==4 else '!d'
            
            if cnt not in [0x4,0x8]:
                raise BPLValueError(cnt,"value must be a 4 or 8 for float lengths.",val_idx-1,self.fname) 
            
            val = struct.unpack(fmt,val)[0]
        
        #Date: 0x30
        elif hi_nib == kCFMarker.Date&0xF0:
            
            if cnt != 8:
                raise BPLValueError(cnt,"value must be a 8 for date lengths.",val_idx-1,self.fname) 
            
            val = self.date_parser( struct.unpack('!d',val)[0] )
        
        elif hi_nib == kCFMarker.Null:
            
            #Null: 0x00
            if lo_nib == kCFMarker.NULL:
                val = None
            
            #False: 0x01, True: 0x02
            elif lo_nib in [kCFMarker.False,kCFMarker.True]:
                val = bool(lo_nib==kCFMarker.True)
            
            #URL: 0x0C, BasedURL: 0x0D
            elif lo_nib in [kCFMarker.URL,kCFMarker.BasedURL]:
                str_mrkr = self.getbyte_int(val_idx)
                
                if str_mrkr&0xF0 != kCFMarker.ASCIIString:
                    raise BPLValueError(str_mrkr,"value's low nibble must be {}, i.e. a string marker.".format(kCFMarker.ASCIIString),val_idx,self.fname)
                
                addlen, val = self.variable_len_object_parser(str_mrkr,val_idx+1)
                total_len += addlen
                
                if lo_nib == kCFMarker.BasedURL:
                    url_idx = val_idx+addlen
                    str2_mrkr = self.getbyte_int(url_idx)
                    
                    if str2_mrkr&0xF0 != kCFMarker.ASCIIString:
                        raise BPLValueError(str2_mrkr,"value's low nibble must be {}, i.e. a string marker.".format(kCFMarker.ASCIIString),url_idx,self.fname)
                    
                    addlen, val2 = self.variable_len_object_parser(str_mrkr,url_idx+1)
                    total_len += addlen
                    
                    val = (val, val2)
            
            #UUID: 0x0E
            elif lo_nib == kCFMarker.UUID:
                uuid2,uuid1 = struct.unpack('!QQ',self._raw_file[val_idx:val_idx+0x10])
                val = CFUUID(uuid2,uuid1)
            
            else:
                raise badmarkererr
        else:
            raise badmarkererr
        
        return total_len, val
    
    def object_parser(self,marker_idx):
        """Takes the index of a BPList object and parses the object
        
        MARKER  BPL_OBJ     PYTHON_VALUE
        0x00    null        None
        0x08    false       False
        0x09    true        True
        0x0F    fill        -----
        0x1*    int         int
        0x2*    real        float
        0x33    date        datetime
        0x4*    data        bytearray
        0x5*    string      str
        0x6*    string      unicode
        0x8*    uid         int
        0xA*    array       list
        0xC*    set         set
        0xD*    dict        dict
        -
        UNUSED MARKERS:
            0x7*, 0x9*, 0xB*, 0xE*, and 0xF* are unused
        
        """
        mrkr = struct.unpack('!B',self._raw_file[marker_idx])[0]
        marker_error = "Object Marker value 0x{:02X} in file {!r} at index {} is not a valid marker value.".format(mrkr,self.fname,marker_idx)
        
        objfmt, ret, bLen = NotImplemented, NotImplemented, 0
        
        if not mrkr&0xF0: #high nibble is 0
            bLen += 1
            
            objfmt = marker_to_type(mrkr)
            
            if mrkr == kCFMarker.Null:
                ret = None
            
            elif mrkr == kCFMarker.Fill:
                ret = ret
            
            elif mrkr == kCFMarker.True or mrkr == kCFMarker.False:
                ret = bool(mrkr==kCFMarker.True)
            
            else:
                try:
                    addlen,ret = self.variable_len_object_parser(mrkr,marker_idx+1)
                except BPLValueError as e:
                    if 'unexpected' in e.reason:
                        raise BPLSyntaxError, marker_error
                    raise
                bLen += addlen-1
        
        else:
            objfmt = marker_to_type(mrkr&0xF0) or marker_to_type(mrkr)
            val_idx = marker_idx+1
            
            addlen,val = self.variable_len_object_parser(mrkr,val_idx)
            bLen += addlen
            
            if mrkr&0xF0 in [kCFMarker.Array,kCFMarker.OrdSet,kCFMarker.Set]:
                ret = []
                for v in val:
                    new_v = self.object_table[v]
                    ret.append(new_v)
            
            elif mrkr&0xF0 == kCFMarker.Dict:
                ret = []
                for k_i,v_i in val:
                    k = self.object_table[k_i]
                    v = self.object_table[v_i]
                    ret.append((k,v))
            
            elif objfmt:
                ret = val
            
            else:
                raise BPLSyntaxError, marker_error
        
        return objfmt, ret, bLen
    
    def __setattr__(self,name,value):
        #Attribute-setting filter
        #
        #if %name% IS in __slots__:
        #   if self.%name% is set:
        #       ERROR
        #   else:
        #       set self.%name%
        #ERROR
        
        try:
            _ = object.__getattribute__(self,name)
        except AttributeError:
            if name not in self.__slots__:
                raise
            else:
                object.__setattr__(self,name,value)
        else:
            raise AttributeError, "{!r} object attribute {!r} is read-only.".format(self.__class__.__name__,name)
    
    def __delattr__(self,attr):
        if attr in dir(self):
            raise TypeError, "can't delete {} attribute".format(attr)
        raise AttributeError, "{!r} object has no attribute {!r}".format(type(self).__name__,attr)
