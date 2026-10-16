#!/usr/bin/env python3
"""Quantify KMS frame parity between device arms (map/title/pause frames).

Reports, per frame pair: the count of differing pixels, the mean and worst
max-channel delta, the share of pixels above a visible-delta threshold, and
the bounding box of the largest localized high-delta cluster. A small number
of localized high-delta pixels is what an animation phase shift looks like;
a broad high-delta field is what a real content difference looks like.
"""
from pathlib import Path
import argparse
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wol_png_lite import read_png, components

VISIBLE = 8


def metrics(a, b):
    w, h, ra = a
    _, _, rb = b
    differing = 0
    total_delta = 0
    over = 0
    worst = 0
    hot = bytearray(w*h)
    for i in range(0, len(ra), 3):
        d = max(abs(ra[i]-rb[i]), abs(ra[i+1]-rb[i+1]), abs(ra[i+2]-rb[i+2]))
        if d:
            differing += 1
            total_delta += d
            if d > worst:
                worst = d
            if d > VISIBLE:
                over += 1
                hot[i//3] = 1
    boxes = components(w, h, hot, min_size=1) if over else []
    clusters = sorted(boxes, key=lambda x: -x['n'])[:4]
    return dict(differing_pixels=differing,
                differing_pct=round(100.0*differing/(w*h), 3),
                mean_max_channel_delta=round(total_delta/(w*h), 4),
                pixels_over_threshold=over,
                pixels_over_threshold_pct=round(100.0*over/(w*h), 4),
                worst_max_channel_delta=worst,
                hot_clusters=[dict(pixels=c['n'], x=c['x0'], y=c['y0'],
                                   w=c['x1']-c['x0']+1, h=c['y1']-c['y0']+1) for c in clusters])


def arm_of(path, pattern):
    m = re.search(pattern, path.name)
    return m.group(1) if m else 'unknown'


def stable_mask(frames):
    """Pixels that carry the same value in every reference frame.

    Pixels that already vary between repeats of one arm are animation or dither
    and cannot testify about parity, so they are excluded explicitly instead of
    being averaged into the verdict.
    """
    w, h, first = frames[0]
    mask = bytearray(b'\x01') * (w*h)
    for _, _, rgb in frames[1:]:
        for i in range(0, len(rgb), 3):
            if mask[i//3] and rgb[i:i+3] != first[i:i+3]:
                mask[i//3] = 0
    return bytes(mask), first, w, h


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('frames', nargs='+', type=Path)
    ap.add_argument('--arm-regex', default=r'([a-z]+)-\d+$',
                    help='first capture group of the parent directory name is the arm')
    ap.add_argument('--scene', required=True, help='scene label shared by these frames')
    ap.add_argument('--out', type=Path, help='write the full report as JSON')
    ap.add_argument('--size', default='1280x720', help='expected WxH of every frame (guards against stray captures)')
    ap.add_argument('--stable-arm', default=None,
                    help='compute the deterministic-pixel mask from this arm and test the others on it')
    a = ap.parse_args()
    want = tuple(int(x) for x in a.size.split('x'))
    loaded = []
    for p in a.frames:
        w, h, rgb = read_png(p)
        if (w, h) != want:
            raise SystemExit('unexpected frame size %dx%d in %s' % (w, h, p))
        loaded.append((str(p), arm_of(p.parent, a.arm_regex), (w, h, rgb)))
    loaded.sort(key=lambda x: x[0])
    report = dict(scene=a.scene, visible_threshold=VISIBLE, frames=[dict(path=p, arm=arm) for p, arm, _ in loaded], pairs=[])
    within = []
    between = []
    for i in range(len(loaded)):
        for j in range(i+1, len(loaded)):
            pa, aa, fa = loaded[i]
            pb, ab, fb = loaded[j]
            m = metrics(fa, fb)
            same = aa == ab
            (within if same else between).append(m)
            report['pairs'].append(dict(a=pa, b=pb, same_arm=same, **m))
    def stats(ms, key):
        xs = [m[key] for m in ms]
        return dict(n=len(xs), min=min(xs) if xs else None, max=max(xs) if xs else None,
                    mean=round(sum(xs)/len(xs), 3) if xs else None)
    report['within_arm'] = {k: stats(within, k) for k in ('differing_pct', 'mean_max_channel_delta', 'pixels_over_threshold_pct')}
    report['between_arm'] = {k: stats(between, k) for k in ('differing_pct', 'mean_max_channel_delta', 'pixels_over_threshold_pct')}
    # Raw differing_pct is dominated by +-1 LSB dither, which is itself random between
    # repeats; parity is therefore judged on amplitude and visible-delta share.
    comparable = bool(within and between) and all(
        report['between_arm'][k]['max'] <= report['within_arm'][k]['max']
        for k in ('mean_max_channel_delta', 'pixels_over_threshold_pct'))
    report['verdict'] = ('no_parity_break_within_same_arm_noise' if comparable else
                         'review: at least one between-arm difference exceeds the same-arm repeat spread')
    report['pairs_with_visible_delta'] = len([p for p in report['pairs'] if p['pixels_over_threshold']])
    report['max_pixels_over_threshold'] = max([p['pixels_over_threshold'] for p in report['pairs']], default=0)
    if a.stable_arm:
        ref = [f for f in loaded if f[1] == a.stable_arm]
        if len(ref) < 2:
            raise SystemExit('need >=2 reference frames for --stable-arm %s' % a.stable_arm)
        mask, first, w, h = stable_mask([f[2] for f in ref])
        stable_px = sum(mask)
        tests = []
        for path, arm, frame in loaded:
            if arm == a.stable_arm:
                continue
            bad = bytearray(w*h)
            n = 0
            total = 0
            over = 0
            worst = 0
            for i in range(0, len(frame[2]), 3):
                if not mask[i//3]:
                    continue
                d = max(abs(frame[2][i]-first[i]), abs(frame[2][i+1]-first[i+1]), abs(frame[2][i+2]-first[i+2]))
                total += d
                if d > worst:
                    worst = d
                if d > VISIBLE:
                    over += 1
                if d:
                    bad[i//3] = 1
                    n += 1
            boxes = components(w, h, bad, min_size=1) if n else []
            tests.append(dict(path=path, arm=arm, stable_pixels_violated=n,
                              violated_pct_of_stable=round(100.0*n/stable_px, 4) if stable_px else None,
                              mean_max_channel_delta_over_frame=round(total/(w*h), 4),
                              stable_pixels_over_threshold=over,
                              worst_max_channel_delta=worst,
                              clusters=[dict(pixels=c['n'], x=c['x0'], y=c['y0'],
                                             w=c['x1']-c['x0']+1, h=c['y1']-c['y0']+1)
                                        for c in sorted(boxes, key=lambda x: -x['n'])[:4]]))
        # Same-arm baseline: how far apart are the reference frames themselves?
        baseline = []
        for i in range(len(ref)):
            for j in range(i+1, len(ref)):
                baseline.append(metrics(ref[i][2], ref[j][2]))
        base = dict(mean_over_frame=round(sum(x['mean_max_channel_delta'] for x in baseline)/len(baseline), 4),
                    worst_share_over_threshold=round(max(x['pixels_over_threshold_pct'] for x in baseline), 4))
        worst_test_mean = max(t['mean_max_channel_delta_over_frame'] for t in tests)
        worst_test_over = max(t['stable_pixels_over_threshold'] for t in tests)
        worst_test_over_pct = round(100.0*worst_test_over/(w*h), 4)
        comparable = (worst_test_mean <= base['mean_over_frame']
                      and worst_test_over_pct <= base['worst_share_over_threshold'])
        base['worst_between_arm_share_over_threshold'] = worst_test_over_pct
        report['stable_mask'] = dict(
            arm=a.stable_arm, reference_frames=[f[0] for f in ref],
            stable_pixels=stable_px, stable_pct=round(100.0*stable_px/(w*h), 3),
            same_arm_repeat_baseline=base,
            violations=tests,
            verdict=('stable_content_identical' if all(t['stable_pixels_violated'] == 0 for t in tests) else
                     'no_parity_break_within_same_arm_noise' if comparable else 'stable_content_differs'))
        print(json.dumps({k: report['stable_mask'][k] for k in ('arm', 'stable_pct', 'same_arm_repeat_baseline', 'verdict')}, indent=2))
        for t in tests:
            print('  ', t['arm'], t['stable_pixels_violated'], 'stable px changed; mean delta',
                  t['mean_max_channel_delta_over_frame'], 'over-threshold', t['stable_pixels_over_threshold'],
                  'worst', t['worst_max_channel_delta'], t['clusters'][:2], t['path'])
    if a.out:
        a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('scene', 'within_arm', 'between_arm',
                                             'pairs_with_visible_delta', 'max_pixels_over_threshold', 'verdict')}, indent=2))
    for p in sorted(report['pairs'], key=lambda x: -x['pixels_over_threshold'])[:3]:
        print('worst:', p['pixels_over_threshold'], 'px >', VISIBLE, p['hot_clusters'], p['a'].split('/')[-2:], p['b'].split('/')[-2:])


if __name__ == '__main__':
    main()
