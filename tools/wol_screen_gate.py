#!/usr/bin/env python3
"""Read-only KMS title readiness gate. A phase/action name is NOT a scene identity.

851 binary luma samples from the stationary WEST OF LOATHING sign (public proof
frame evidence/uprender-scope/upscope-a1/title.png, SHA256 f23f1f93b27f103faa8a25584964a3525c64355dae5b3b46d524771053aa5b6d).
Matches only this game's verified 1280x720 title; fail closed on other dimensions.
Not an OCR or general scene classifier, and not gameplay/physical-input evidence.
"""
from pathlib import Path
from typing import Any
import struct
import zlib
import time

TITLE_BITS=bin(int('fbddc0de07eade06f01a54a03280d321009c079c8804c018a8402600cf760720027b301b000000000000000000000000000000000000000040e00000c62f7b2dc23151495e115a8a4ac088c4727405462213ac2b29009543dbd9edae1edecf6d30000000000',16))[2:].zfill(851)
TITLE_POINTS=tuple((x,y) for y in range(150,330,8) for x in range(610,900,8))


def read_rgb(path):
    data=Path(path).read_bytes()
    if len(data)>16*1024*1024 or not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('bounded PNG required')
    pos=8;compressed=[];shape=None
    while pos+12<=len(data):
        n=struct.unpack_from('>I',data,pos)[0]
        if n>len(data)-pos-12:raise ValueError('truncated PNG chunk')
        kind=data[pos+4:pos+8];body=data[pos+8:pos+8+n];pos+=n+12
        if kind==b'IHDR':shape=struct.unpack('>IIBBBBB',body)
        if kind==b'IDAT':compressed.append(body)
    if not shape:raise ValueError('missing PNG header')
    w,h,b,c,compression,filtering,interlace=shape
    if not (0<w<=4096 and 0<h<=4096 and (b,c,compression,filtering,interlace)==(8,2,0,0,0)):
        raise ValueError('non-interlaced RGB8 KMS capture required')
    size=(w*3+1)*h;d=zlib.decompressobj();raw=d.decompress(b''.join(compressed),size+1)
    if len(raw)!=size or not d.eof:raise ValueError('PNG decompressed length mismatch')
    stride=w*3;result=bytearray(stride*h);previous=bytes(stride)
    for y in range(h):
        start=y*(stride+1);f=raw[start];row=bytearray(raw[start+1:start+1+stride])
        if f not in range(5):raise ValueError('unknown PNG filter')
        if f:
            for x in range(stride):
                a=row[x-3] if x>=3 else 0;b=previous[x];c=previous[x-3] if x>=3 else 0
                if f==1:v=a
                elif f==2:v=b
                elif f==3:v=(a+b)//2
                else:
                    p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c)
                    v=a if pa<=pb and pa<=pc else (b if pb<=pc else c)
                row[x]=(row[x]+v)&255
        result[y*stride:(y+1)*stride]=row;previous=row
    return w,h,result


def fingerprint_match(w,rgb,points,bits,dx_values,dy_values):
    best=1.0;offset=None
    for dy in dy_values:
        for dx in dx_values:
            different=0
            for (x,y),expected in zip(points,bits):
                i=((y+dy)*w+x+dx)*3
                black=rgb[i]+rgb[i+1]+rgb[i+2]<360
                different+=black!=(expected=='1')
            mismatch=different/len(bits)
            if mismatch<best:best=mismatch;offset=[dx,dy]
    return best,offset


def title_observation(path) -> dict[str,Any]:
    w,h,rgb=read_rgb(path)
    if (w,h)!=(1280,720):return dict(is_title=False,reason='unsupported shape',width=w,height=h)
    best,offset=fingerprint_match(w,rgb,TITLE_POINTS,TITLE_BITS,range(-8,9,2),range(-12,13,2))
    return dict(is_title=best<=0.14,mismatch=best,best_offset=offset,samples=len(TITLE_BITS),
                scope='known title sign only; not game-state proof')


def wait_for_title(capture,path,is_alive,record,seconds=300,period=7,now=time.monotonic,pause=time.sleep):
    """Transient capture absence is allowed; wrong/dead PID and deadline are not."""
    deadline=now()+seconds
    while True:
        if not is_alive():raise RuntimeError('runtime identity changed while waiting for title')
        try:
            capture();observed=title_observation(path)
        except (OSError,RuntimeError,ValueError) as error:
            observed=dict(is_title=False,capture_error=str(error))
        observed['t_ns']=time.monotonic_ns();record(observed)
        if observed['is_title']:return observed
        remaining=deadline-now()
        if remaining<=0:raise RuntimeError('verified title deadline exceeded; CONTINUE refused')
        pause(min(period,remaining))


HUD_BITS=bin(int('1000028060040210a1f705100228401140000a2082520a02907090c00082004408002850717f340004c0052000',16))[2:].zfill(357)
HUD_POINTS=tuple((x,y) for y in range(10,78,4) for x in range(1192,1276,4))


def gameplay_observation(path):
    w,h,rgb=read_rgb(path)
    if (w,h)!=(1280,720):return dict(has_game_hud=False,reason='unsupported shape')
    best,offset=fingerprint_match(w,rgb,HUD_POINTS,HUD_BITS,range(-4,5),range(-4,5))
    return dict(has_game_hud=best<=0.08,mismatch=best,best_offset=offset,
                scope='known gameplay settings-gear HUD, not scene/battle identity or physical input')
