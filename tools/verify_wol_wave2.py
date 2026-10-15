#!/usr/bin/env python3
"""Independent acceptance test for staged M4 wave2; no writes to game data.
Compare every object against accepted M4; only explicitly selected textures and
its dependent Sprite pixel metadata may differ. Check selected pixels against
the corresponding original mip slice, not a new resize.
"""
from pathlib import Path
import argparse
import copy
import json

import UnityPy
from UnityPy.enums import TextureFormat
from wol_memory_repack import level0_size, mip_chain_size, scale_sprite_pixel_metadata


def levels(path):
    return {int(l.split('\t')[0]):int(l.split('\t')[1]) for l in path.read_text().splitlines() if l and not l.startswith('#')}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('original','baseline','candidate','baseline-levels','candidate-levels','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    blevels,clevels=levels(a.baseline_levels),levels(a.candidate_levels)
    assert all(clevels[k]==v for k,v in blevels.items()), 'accepted baseline ID changed'
    extra=set(clevels)-set(blevels)
    baseline=UnityPy.load(str(a.baseline))
    candidate=UnityPy.load(str(a.candidate))
    def objects(env):
        result={}
        for x in env.objects:
            key=(x.assets_file.name,x.path_id)
            assert key not in result, 'duplicate identity'
            result[key]=x
        return result
    bo,co=objects(baseline),objects(candidate)
    assert bo.keys()==co.keys(), 'object identities changed'
    payload=0
    changed_textures=[]
    changed_sprites=[]
    unchanged=0
    selected_meta={}
    for key,x in co.items():
        old=bo[key]
        if x.type.name=='Texture2D' and x.path_id in extra:
            before,d=old.read(),x.read()
            assert int(before.m_TextureFormat)==int(d.m_TextureFormat), 'format changed'
            assert d.m_MipCount==before.m_MipCount==1 and d.m_ImageCount==before.m_ImageCount==1
            assert (d.m_Width,d.m_Height)==(before.m_Width//2,before.m_Height//2), 'unexpected resize'
            fmt=TextureFormat(d.m_TextureFormat).name
            expected=level0_size(d.m_Width,d.m_Height,fmt)
            assert len(bytes(d.image_data))==d.m_CompleteImageSize==expected
            selected_meta[x.path_id]=(d.m_Width,d.m_Height,bytes(d.image_data))
            changed_textures.append(x.path_id)
        elif x.type.name=='Sprite':
            b,d=old.read_typetree(),x.read_typetree()
            ref=b['m_RD']['texture']
            if ref['m_FileID']==0 and ref['m_PathID'] in extra:
                expected=copy.deepcopy(b)
                scale_sprite_pixel_metadata(expected,0.5,ui=False)
                assert expected==d, 'dependent sprite metadata mismatch'
                changed_sprites.append(x.path_id)
            else:
                assert x.get_raw_data()==old.get_raw_data(), 'unselected sprite changed'
                unchanged+=1
        else:
            assert x.get_raw_data()==old.get_raw_data(), f'unselected object changed {key}'
            unchanged+=1
        if x.type.name=='Texture2D':
            payload+=x.read().m_CompleteImageSize
    assert set(changed_textures)==extra, 'missing candidate'
    del baseline,candidate,bo,co
    original=UnityPy.load(str(a.original))
    exact=0
    for x in original.objects:
        if x.type.name!='Texture2D' or x.path_id not in extra:
            continue
        s=x.read()
        fmt=TextureFormat(s.m_TextureFormat).name
        steps=1+(clevels[x.path_id])
        prefix=mip_chain_size(s.m_Width,s.m_Height,fmt,steps)
        assert prefix is not None, 'unsupported mip format'
        w,h,raw=selected_meta[x.path_id]
        assert (w,h)==(s.m_Width>>steps,s.m_Height>>steps)
        assert raw==bytes(s.image_data)[prefix:prefix+len(raw)], 'not byte-exact original mip'
        exact+=1
    assert exact==len(extra)
    result=dict(schema=1,status='STAGED_VERIFIED_NOT_DEPLOYED',objects=len(objects(original)),
        changed_textures=len(changed_textures),changed_sprites=len(changed_sprites),
        byte_exact_original_mip_slices=exact,unchanged_objects_byte_exact=unchanged,
        candidate_payload_bytes=payload,candidate_bundle_bytes=a.candidate.stat().st_size,
        caveat='Offline structure/pixel check only. No device quality, RAM or FPS claim.')
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
