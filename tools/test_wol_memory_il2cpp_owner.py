import struct
import unittest
from wol_il2cpp23_owner import OwnerMap


def fixture():
    strings=b'UpRender\0Other\0forceWidth\0forceHeight\0Awake\0UpdateTexture\0.ctor\0'
    ix=lambda name:strings.index(name.encode()+b'\0')
    h=[0]*66;h[:2]=[0xFAB11BAF,23];body=bytearray(264)
    def add(pair,blob):
        h[pair:pair+2]=[len(body),len(blob)];body.extend(blob)
    add(6,strings)
    rows=[]
    for i,(owner,name) in enumerate([(0,'Awake'),(0,'UpdateTexture'),(1,'.ctor'),(1,'Awake')]):
        row=[ix(name),owner,0,0,0,-1,i,0,-1,-1,0,0,0,0,0,0]
        rows.append(struct.pack('<12i4H',*row))
    add(12,b''.join(rows))
    add(24,struct.pack('<4i',ix('forceWidth'),0,0,0)+struct.pack('<4i',ix('forceHeight'),0,0,0))
    types=[]
    for i,name in enumerate(('UpRender','Other')):
        t=[0]*30;t[0]=ix(name);t[12]=0 if not i else -1;t[13]=i*2;t[20]=2;t[22]=2 if not i else 0
        types.append(struct.pack('<20i8H2I',*t))
    add(40,b''.join(types));struct.pack_into('<66I',body,0,*h)
    text=bytes(0x200);ro=bytearray(0x100);struct.pack_into('<2i',ro,0,32,36)
    data=bytearray(0x500)
    struct.pack_into('<4Q',data,0,0x10,0x20,0x30,0x40)
    struct.pack_into('<2Q',data,0x200,0x1000,0)
    struct.pack_into('<2Q',data,0x240,0x1080,0x1090)
    struct.pack_into('<2Q',data,0x280,4,0x2000)
    struct.pack_into('<4Q',data,0x300,2,0x2200,2,0x2240)
    return bytes(body),text,bytes(ro),bytes(data),0x1000,0x2000


class Metadata23Tests(unittest.TestCase):
    def test_native_methods_and_fields_join_independent_literal_fixture(self):
        m=OwnerMap(*fixture());x=m.type_report('UpRender')
        self.assertEqual(x['methods'],[{'name':'Awake','method_index':0,'native_offset':0x10},
                                      {'name':'UpdateTexture','method_index':1,'native_offset':0x20}])
        self.assertEqual(x['fields'],[{'name':'forceWidth','offset':32},{'name':'forceHeight','offset':36}])
        self.assertEqual(m.type_report('Other')['fields'],[])

    def test_version_range_ambiguity_and_unknown_type_refuse(self):
        a=list(fixture());bad=bytearray(a[0]);struct.pack_into('<I',bad,4,24);a[0]=bytes(bad)
        with self.assertRaisesRegex(ValueError,'v23'):OwnerMap(*a)
        a=list(fixture());bad=bytearray(a[3]);struct.pack_into('<2Q',bad,0x380,4,0x2000);a[3]=bytes(bad)
        with self.assertRaisesRegex(ValueError,'ambiguous'):OwnerMap(*a)
        a=list(fixture());bad=bytearray(a[3]);struct.pack_into('<Q',bad,0x288,0x9999999);a[3]=bytes(bad)
        with self.assertRaises(ValueError):OwnerMap(*a)
        with self.assertRaisesRegex(ValueError,'type missing'):OwnerMap(*fixture()).type_report('Unknown')


if __name__=='__main__':unittest.main()
