"""Exact hashes/stages for the two observed post-splash menu shaders."""
from pathlib import Path
import re
import unittest


class UpdateMenuShaderTests(unittest.TestCase):
    def test_observed_pair_is_pinned_by_code_and_control_not_a_generic_fallback(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        expected=[
            ('56844c6b',1024,0,'56844c6ba737e9ef8558ff6f0fb935e867fe26fa0ab8be1d65f2125ab327c48f','624dd9d115390db5c07cfeccd30d37cbd3aa5af82903ea710814d365aedfde87'),
            ('7227c812',512,1,'7227c812dba30ea82b90fc43945f4156fea1c4efaf4467da8c5f102b30f21588','747fc79cddd935afe0dab5765a24b9718c2136561151c234921c64cf0b15c3f6'),
            ('6a930d0e-ui',1024,0,'6a930d0edea444e0a29d3db880fe76203b4fa12aa959fa8dfbcb7b001cee71dd','44d94f837f0c7aa028a9517c1777ae5a59c33974bffac0b5d53936773a875939'),
            ('06993fc8',768,1,'06993fc833fade5562bb4dc7f0fe5449f660dbb98c2b514234714e1cb6922be6','67813bccc51f4b8965264aedef538282384e83883f5fa5dff443c7705dd5e343'),
            ('e56d57b0',768,0,'e56d57b0e6e05a64a23a6591c46c72ba333f2aad098cecbdea246f641c9febc1','74042df4297c014004e9094b48a908d4d5471ac73ace6e636e9e5248939beef2'),
            ('33d1c25c',256,1,'33d1c25c097ec2bea1e45b267ca1eaab1afe9c3dcdca741688e7263faf1a13bd','656623733665459e6d2d18af91e1046711f37189fc93a6eb06004503e5bf82d7'),
            ('6054acba-mesh',768,0,'6054acba873a0922637dff386f4e1313f453e0e7c23a026106744eafb7c2b99a','393ba0cd7b4d2d3c8de59342c8ba24db487465a04133b4f57744ec91efdb5ad5'),
            ('3236d4e6-mesh',512,1,'3236d4e624cb592720be5c33be49eccc76187cccdd01cce9fd95b37bc89c927e','dcdb91430fe303100abbd4454d237c4bd0051ddd7ee7d4e92d1fbfcab710b177'),
            ('a4245675-mesh',768,0,'a4245675abbc5cd5e29de73409da533ab8c12ddd711e17ab9970647a73e09d74','1306744f0ec3b49d573276fadb2ce36770ec084cd81ec4587576701f2d9c025c'),
            ('2bad7d7d-mesh',512,1,'2bad7d7daad2aa97403f56eed0be91f603d809a6b6b8a8bd5e4a3bad996f75e4','189f11173fecd37a94007668600a0f46aae9b2811d3c4d47fe92bd7f169f2937'),
        ]
        for name,size,stage,code,control in expected:
            with self.subTest(shader=name):
                match=re.search(r'\{'+str(size)+r',0x880,'+str(stage)+r',1,"update-'+name+r'-diagnostic",[^,]+,\s*\{([^}]+)\},\s*\{([^}]+)\}',added)
                self.assertTrue(match is not None,'missing exact diagnostic entry '+name)
                assert match is not None
                hashes=[bytes(int(b,16) for b in re.findall(r'0x[0-9a-f]+',match[i])).hex() for i in (1,2)]
                self.assertEqual(hashes,[code,control])
        self.assertTrue('a_pos.xy*vec2(c3[36],c3[37])' in added,'missing SASS position pre-scale')
        self.assertTrue('a_col*vec4(c3[32],c3[33],c3[34],c3[35])*vec4(c3[40],c3[41],c3[42],c3[43])' in added,'missing both SASS tint factors')
        self.assertTrue('vec4(c.rgb*c.a,c.a)' in added,'missing premultiplied fragment output')


    def test_update_sprite_fragment_does_not_divide_perspective_varyings_twice(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        fragment=added.split('static const char wol_update_800121db_glsl[]=',1)[1].split('/* Post-splash pair:',1)[0]
        self.assertIn('texture2D(tex0,v_uv)',fragment,
                      'Maxwell IPA reciprocal-w is already represented by GLES perspective interpolation')
        self.assertNotIn('v_uv/v_clip.w',fragment)

    def test_observed_mesh_mask_keeps_uniform_rgb_and_texture_alpha_separate(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        self.assertTrue('static const char wol_update_6054acba_glsl[]=' in added,'missing measured mesh vertex')
        self.assertTrue('static const char wol_update_3236d4e6_glsl[]=' in added,'missing measured mesh mask fragment')
        vertex=added.split('static const char wol_update_6054acba_glsl[]=',1)[1].split('static const char wol_update_3236d4e6_glsl[]=',1)[0]
        fragment=added.split('static const char wol_update_3236d4e6_glsl[]=',1)[1].split('/* WOL_UPDATE_MESH_END */',1)[0]
        self.assertIn('v_uv=a_extra',vertex,'a[0x90,0x94] is guest attribute1, not sprite UV attribute2')
        self.assertIn('mul4(16,mul4(0,vec4(a_pos,1.0)))',vertex)
        self.assertIn('texture2D(tex0,v_uv).a*c3f[3]',fragment)
        self.assertIn('vec4(c3f[4],c3f[5],c3f[6],alpha)',fragment)
        self.assertNotIn('/v_clip.w',fragment)
        self.assertNotIn('discard',fragment,'the measured mesh mask has no alpha-test shortcut')

    def test_farm_mesh_samples_perspective_correct_uv_without_a_second_divide(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        marker='static const char wol_update_2bad7d7d_mesh_glsl[]='
        self.assertTrue(marker in added,'missing farm mesh material observed while torsos are absent')
        fragment=added.split(marker,1)[1].split('/* WOL_UPDATE_MESH_END */',1)[0]
        self.assertIn('texture2D(tex0,v_extra)',fragment)
        self.assertIn('vec4(c3f[0],c3f[1],c3f[2],c3f[3])',fragment)
        self.assertNotIn('/v_pos.w',fragment)
        self.assertNotIn('discard',fragment)


if __name__=='__main__':
    unittest.main()
