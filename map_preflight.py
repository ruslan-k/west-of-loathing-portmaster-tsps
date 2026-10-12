#!/usr/bin/env python3
"""Experimental NSO mapping/relocation preflight, NEVER executes Switch code.
Host-independent data-stage test only; not a Horizon/NVN compatibility runtime.
"""
import argparse, collections, ctypes, hashlib, json, mmap, pathlib, struct


def preflight(root, report):
    mappings = {}
    modules = report['modules']
    namespace = {}
    totals = collections.Counter()
    try:
        for module in modules:
            name = module['module']
            span = (module['mapped_bytes'] + mmap.PAGESIZE - 1) & -mmap.PAGESIZE
            memory = mmap.mmap(-1, span, prot=mmap.PROT_READ | mmap.PROT_WRITE)
            address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
            mappings[name] = memory, address
            for segment in module['segments']:
                data = (root/'segments'/(name+'.'+segment['name']+'.seg')).read_bytes()
                if len(data) != segment['size'] or hashlib.sha256(data).hexdigest() != segment['sha256']:
                    raise ValueError('segment identity mismatch: '+name)
                start = segment['address']
                memory[start:start+len(data)] = data
            end = max(s['address']+s['size'] for s in module['segments'])
            if any(memory[end:end+module['bss_bytes']]):
                raise ValueError('BSS not zero initialized')
        # rtld-first namespace. Do not confuse resolved guest exports with host ABI support.
        order = sorted(modules,key=lambda m: ['rtld','main','subsdk0','sdk'].index(m['module']))
        for module in order:
            address = mappings[module['module']][1]
            for symbol in module['symbol_slots']:
                if not symbol['name'] or not symbol['defined'] or symbol['binding'] not in (1,2):
                    continue
                resolved = symbol['value'] if symbol['section'] == 0xfff1 else address+symbol['value']
                existing = namespace.get(symbol['name'])
                if existing is None or (existing[1] == 2 and symbol['binding'] == 1):
                    namespace[symbol['name']] = resolved, symbol['binding']
        for module in modules:
            name = module['module']
            memory, address = mappings[name]
            for relocation in module['relocations']:
                kind = relocation['type']
                if kind == 1027:
                    result = address + relocation['addend']
                elif kind in (257,1025,1026):
                    symbol = module['symbol_slots'][relocation['symbol_index']]
                    if symbol['binding'] == 0 and symbol['defined']:
                        target = address + symbol['value']
                    elif symbol['name'] in namespace:
                        target = namespace[symbol['name']][0]
                    elif symbol['binding'] == 2:
                        target = 0
                    else:
                        raise ValueError('unresolved strong relocation: '+symbol['name'])
                    result = target + relocation['addend']
                else:
                    raise ValueError('unsupported relocation type: '+str(kind))
                offset = relocation['target']
                struct.pack_into('<Q',memory,offset,result & ((1<<64)-1))
                if struct.unpack_from('<Q',memory,offset)[0] != result & ((1<<64)-1):
                    raise ValueError('relocation read-back failed')
                totals[kind] += 1
        result = dict(verdict='DATA_STAGE_PASS_EXECUTION_NOT_ATTEMPTED', modules=len(modules), mapped_bytes=sum(len(m[0]) for m in mappings.values()), relocations_applied_and_read_back=sum(totals.values()), relocation_types=dict(totals), strong_guest_imports_unresolved=0, execution_enabled=False, blockers=['No Horizon SVC/IPC implementations installed', 'Guest TPIDR_EL0 access needs isolation from host TLS', 'No West of Loathing NVN/shader adapter', 'No title frame/audio/input/memory validation'], note='mmap is host-native RW data only, never executable; resolving SDK exports does NOT implement the operating system underneath them.')
        return result
    finally:
        for memory,address in mappings.values():
            memory.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=pathlib.Path)
    parser.add_argument('--report',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args = parser.parse_args()
    result = preflight(args.root,json.loads(args.report.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
