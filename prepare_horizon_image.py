#!/usr/bin/env python3
"""Generate owner-only WoL base NSO/RomFS contracts for the recovered Horizon runtime.
Output includes proprietary owner data; never publish it. Shader translation is NOT supplied.
"""
import argparse,hashlib,json,pathlib,shutil,struct,subprocess,sys
from inspect_nso import inspect_nso

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('exefs','npdm_json','romfs_json','output'): p.add_argument(name,type=pathlib.Path)
    a=p.parse_args()
    npdm=json.loads(a.npdm_json.read_text()); rom=json.loads(a.romfs_json.read_text())
    if int(npdm['title_id'],16)!=0x010031b00a4e8000 or not npdm['is_64_bit']: raise ValueError('unsupported title/ABI')
    services=npdm.get('service_access')
    if not isinstance(services,list) or any(not isinstance(n,str) or not 1<=len(n)<=8 or not n.isascii() or '\0' in n for n in services):
        raise ValueError('invalid NPDM service names; regenerate metadata with hactool -t npdm --json=FILE')
    section=pathlib.Path(rom['section'])
    if section.stat().st_size!=rom['section_size'] or digest(section)!=rom['sha256']: raise ValueError('RomFS identity mismatch')
    if rom['romfs_offset']+rom['romfs_size']>rom['section_size']: raise ValueError('RomFS bounds')
    mods={n:inspect_nso(a.exefs/n) for n in ('rtld','main','subsdk0','sdk')}
    if a.output.exists(): raise ValueError('output must not exist')
    subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('prepare_image.py')),str(a.exefs),str(a.output)],check=True)
    for f in (a.output/'segments').iterdir(): shutil.move(f,a.output/f.name)
    (a.output/'segments').rmdir()
    bases={}; base=0x08000000; entries=[]
    for name,m in mods.items():
        bases[name]=base
        for s in m['segments']:
            size=s['size']+(m['bss_bytes'] if s['name']=='data' else 0)
            aligned=(size+4095)&~4095
            perm=5 if s['name']=='text' else 3 if s['name']=='data' else 1
            state=4 if s['name']=='data' else 3
            entries.append('    {"%s.%s.seg",0x%xULL,%dULL,%dULL,%d,%d},'%(name,s['name'],base+s['address'],s['size'],aligned,perm,state))
        base+=((m['mapped_bytes']+4095)&~4095)+4096
    sdk=mods['sdk']; text=(a.output/'sdk.text.seg').read_bytes()
    symbols={s['name']:s for s in sdk['symbols'] if s['defined']}
    bootstrap=symbols['nvnBootstrapLoader']['value']; internal=symbols['nvnBootstrapLoaderInternal']['value']

    def resolve_lookup(entry):
        """Locate the SDK's NVN object lookup thunk from the exported bootstrap entry.

        Two measured shapes exist:
          A (base v0): the entry branches (BL) to the thunk itself.
          B (update v327680): the entry tail-branches (B) to the thunk.
        The thunk itself is version-stable: adrp x8,<page>; ldr x8,[x8,#imm];
        ldr x2,[x8]; br x2 - a jump through a relocated pointer slot.
        """
        found=None
        for index in range(6):
            word=struct.unpack_from('<I',text,entry+index*4)[0]
            if word&0xfc000000 not in (0x14000000,0x94000000):
                continue
            delta=word&0x3ffffff
            if delta&0x2000000:
                delta-=0x4000000
            candidate=entry+index*4+delta*4
            adrp,ldr,indirect,jump=struct.unpack_from('<4I',text,candidate)
            if adrp&0x9f00001f!=0x90000008 or ldr&0xffc003ff!=0xf9400108 or indirect!=0xf9400102 or jump!=0xd61f0040:
                continue
            imm=((adrp>>29)&3)|(((adrp>>5)&0x7ffff)<<2)
            if imm&0x100000:
                imm-=0x200000
            slot=(candidate&~4095)+imm*4096+((ldr>>10)&0xfff)*8
            relocation=next((r for r in sdk['relocations'] if r['target']==slot and r['type']==1027),None)
            if not relocation:
                continue
            found=(candidate,adrp,slot,relocation['addend'])
            break
        if not found:
            raise ValueError('unsupported lookup thunk; do not assume Tegra ABI')
        return found

    entry=internal
    first=struct.unpack_from('<I',text,internal+12)[0]
    if (first&0xfc000000)==0x14000000 or (first&0xfc000000)==0x94000000:
        entry=internal+12
    lookup,adrp,lookup_slot,addend=resolve_lookup(entry)
    pointer=bases['sdk']+addend
    # Builder device-pointer convention. The base v0 SDK was pinned by device runs 01-03 to three
    # exact setters (str x1,[x0]; ret, device at +0). A different game revision moves those RVAs,
    # so the check is applied to the known module and replaced by the measured pattern otherwise;
    # the runtime reads the device pointer at +0 in both cases.
    known_v0_sdk='3c5fc6933f619271feb42f62519e9f9043d06f3ee76746552b6b4cfe9094537e'
    setters=(0x2c5238,0x2c154c,0x2b6590)
    if sdk['sha256']==known_v0_sdk:
        for rva in setters:
            if struct.unpack_from('<II',text,rva)!=(0xf9000001,0xd65f03c0):
                raise ValueError('unproven WoL builder ABI at %#x; reject rather than borrowing offset'%rva)
        builder_note='builder-setters=pinned-rvas'
    else:
        if any(struct.unpack_from('<II',text,rva)==(0xf9000001,0xd65f03c0) for rva in setters):
            raise ValueError('builder RVA coincidence on an unknown module; refusing')
        pattern=struct.pack('<II',0xf9000001,0xd65f03c0)
        sites=[];at=text.find(pattern)
        while at!=-1:
            sites.append(at);at=text.find(pattern,at+1)
        if len(sites)<3:
            raise ValueError('builder setter pattern not found on unknown module')
        builder_note='builder-setters=pattern-verified count=%d device-offset=0'%len(sites)

    # Index zero in graphics_trace is deliberately disabled until nvInitializeGraphics is identified.
    g=['/* Generated owner-specific graphics identity. No translated shaders. */',
       '#define LC2_GRAPHICS_INIT_PC 0ULL','#define LC2_GRAPHICS_INIT_OPCODE 0U',
       '#define LC2_GRAPHICS_BOOTSTRAP_PC 0x%xULL'%(bases['sdk']+bootstrap),
       '#define LC2_GRAPHICS_BOOTSTRAP_OPCODE 0x%xU'%struct.unpack_from('<I',text,bootstrap)[0],
       '#define LC2_GRAPHICS_LOOKUP_PC 0x%xULL'%(bases['sdk']+lookup),
       '#define LC2_GRAPHICS_LOOKUP_OPCODE 0x%xU'%adrp,
       '#define LC2_NVN_LOOKUP_POINTER 0x%xULL'%pointer]
    (a.output/'megaman_graphics_contract.h').write_text('\n'.join(g)+'\n')
    # Process address-space flavour: NPDM MMU flags bit 4 (OptimizeMemoryAllocation) means the title
    # declares a system resource region. nvn/os VammManager only enables itself when svcGetInfo
    # InfoType 16 (SystemResourceSizeTotal) is non-zero, and the Unity-2019 runtime calls
    # nn::os::AllocateAddressRegion unconditionally at init - with a zero size the manager object
    # stays NULL and the first allocation dereferences it (measured: CPU_FAULT sdk+0x341e70,
    # detail 0xc0 = [manager+0x40]+0x18+0xa8 with manager NULL). The NPDM itself is read from the
    # verified module directory, not assumed.
    sysres=0
    npdm_path=a.exefs/'main.npdm'
    if npdm_path.is_file():
        npdm_bytes=npdm_path.read_bytes()
        if npdm_bytes[:4]==b'META':
            mmu=npdm_bytes[12]  # NpdmFlags byte (0x07 base, 0x17 update: bit 4 = OptimizeMemoryAllocation)
            if mmu&0x10:
                sysres=0x1000000
    if sysres:
        print('System resource declared by the NPDM (MMU flags bit 4): reporting %d MiB'%(sysres>>20))
    h=['/* Generated local owner image; not redistributable game payload. */',
       '#define LC2_PROGRAM_ID 0x%xULL'%int(npdm['title_id'],16),
       '#define LC2_MAIN_STACK_SIZE %dULL'%int(npdm['main_thread_stack_size'],16),
       '#define LC2_MAIN_PRIORITY %d'%npdm['main_thread_priority'],
       '#define LC2_MAIN_CORE %d'%npdm['default_cpu_id'],
       '#define LC2_ALLOWED_CORE_MASK 7ULL',
       '#define LC2_ALLOWED_PRIORITY_MASK 0x%xULL'%sum(1<<i for i in range(28,60)),
       '#define LC2_SYSTEM_RESOURCE_SIZE %dULL'%sysres,
       '#define WOL_NVN_QUEUE_BUILDER_OFFSET 0ULL',
       '#define WOL_NVN_POOL_BUILDER_OFFSET 0ULL',
       '#define WOL_NVN_BUFFER_BUILDER_OFFSET 0ULL',
       '#define WOL_SHADER_CAPTURE 1',
       '#define WOL_SAMPLER_LEGACY_LAYOUT 1',
       '#define WOL_TEXTURE_BUILDER_UNPREFIXED 1',
       '#define WOL_WINDOW_BUILDER_UNPREFIXED 1',
       '#define WOL_MSAA_DOWNGRADE 1',
       '#define WOL_PLACEHOLDER_COMMANDS 1',
       '#define WOL_TEXTURE_VIEW_36 1',
       '#define WOL_DIAGNOSE_HOST_FAULT 1',
       '#define ROMFS_SECTION_NAME "wol-romfs.section"',
       '#define ROMFS_SECTION_SIZE %dULL'%rom['section_size'],
       '#define ROMFS_OFFSET %dULL'%rom['romfs_offset'],
       '#define ROMFS_SIZE %dULL'%rom['romfs_size'],
       '#define FILESYSTEM_ROMFS_READ_LIMIT (256ULL<<20)',
       '#define LC2_ROMFS_SHA256 "%s"'%rom['sha256']]
    for name,m in mods.items():
        prefix='LC2_'+name.upper()
        h+=['#define %s_BASE 0x%xULL'%(prefix,bases[name]),'#define %s_IMAGE_SIZE %dULL'%(prefix,m['mapped_bytes']),'#define %s_SHA256 "%s"'%(prefix,m['sha256'])]
    h+=['static const char *const allowed_services[]={'+','.join(json.dumps(n) for n in services)+'};','static const struct image_segment images[]={',*entries,'};']
    (a.output/'image_table.h').write_text('\n'.join(h)+'\n')
    (a.output/'megaman_lc2_contract.h').write_text('/* Disabled inherited title-specific profile; WoL owner image_table.h supplies the contract. */\n')
    shutil.copy2(section,a.output/'wol-romfs.section')
    print('Owner contracts generated; graphics-init observer disabled; shader translation absent.')
    print('NVN lookup thunk:',hex(bases['sdk']+lookup),'object:',hex(pointer))

if __name__=='__main__': main()
