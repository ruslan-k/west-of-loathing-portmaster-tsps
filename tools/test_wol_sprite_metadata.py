#!/usr/bin/env python3
"""Pixel metadata must follow mip promotion; local geometry and baked UVs must not."""
import copy
import unittest
import wol_memory_repack as repack

class SpriteMetadataTests(unittest.TestCase):
    def setUp(self):
        # Synthetic Unity 5.6-shaped fixture, not game data.
        self.sprite = {
            'm_Rect': dict(x=100., y=50., width=80., height=120.),
            'm_Offset': dict(x=4., y=-2.),
            'm_Border': dict(x=2., y=4., z=6., w=8.),
            'm_PixelsToUnits': 3.,
            'm_Pivot': dict(x=.5,y=.5),
            'm_RD': {
                'textureRect':dict(x=100.,y=50.,width=80.,height=120.),
                'textureRectOffset':dict(x=4.,y=6.),
                'atlasRectOffset':dict(x=-1.,y=-1.),
                'uvTransform':dict(x=3.,y=140.,z=3.,w=110.),
                'm_VertexData':{'m_DataSize':b'unchanged normalized UV and local XYZ'},
                'm_IndexBuffer':[0,1,2],
            },
        }

    def repair(self,scale):
        fn=getattr(repack,'scale_sprite_pixel_metadata',None)
        self.assertTrue(callable(fn), 'mip promotion lacks sprite pixel metadata repair')
        return fn(self.sprite,scale)

    def test_normalized_rect_unchanged_after_dimension_halving(self):
        old=copy.deepcopy(self.sprite)
        self.repair(.5)
        for key in ('x','width'):
            self.assertEqual(self.sprite['m_RD']['textureRect'][key]/256,
                             old['m_RD']['textureRect'][key]/512)
        for key in ('y','height'):
            self.assertEqual(self.sprite['m_RD']['textureRect'][key]/128,
                             old['m_RD']['textureRect'][key]/256)

    def test_local_geometry_and_baked_uvs_unchanged(self):
        old=copy.deepcopy(self.sprite)
        self.repair(.5)
        self.assertEqual(self.sprite['m_Rect'], old['m_Rect'])
        self.assertEqual(self.sprite['m_Offset'], old['m_Offset'])
        self.assertEqual(self.sprite['m_Border'], old['m_Border'])
        self.assertEqual(self.sprite['m_PixelsToUnits'], old['m_PixelsToUnits'])
        self.assertEqual(self.sprite['m_Rect']['width']/self.sprite['m_PixelsToUnits'],
                         old['m_Rect']['width']/old['m_PixelsToUnits'])
        self.assertEqual(self.sprite['m_RD']['m_VertexData'],old['m_RD']['m_VertexData'])
        self.assertEqual(self.sprite['m_Pivot'],old['m_Pivot'])
        self.assertEqual(self.sprite['m_RD']['m_IndexBuffer'],old['m_RD']['m_IndexBuffer'])
        self.assertEqual(self.sprite['m_RD']['atlasRectOffset'],old['m_RD']['atlasRectOffset'])
        for key in ('x','y','z','w'):
            self.assertEqual(self.sprite['m_RD']['uvTransform'][key],old['m_RD']['uvTransform'][key]*.5)

    def test_ui_pixel_rect_tracks_padding_and_preserves_size(self):
        old=copy.deepcopy(self.sprite)
        repack.scale_sprite_pixel_metadata(self.sprite, .5, ui=True)
        self.assertEqual(self.sprite['m_Rect']['width'], old['m_Rect']['width']*.5)
        self.assertEqual(self.sprite['m_PixelsToUnits'], old['m_PixelsToUnits']*.5)
        self.assertEqual(self.sprite['m_Rect']['width']/self.sprite['m_PixelsToUnits'],
                         old['m_Rect']['width']/old['m_PixelsToUnits'])
        self.assertEqual(self.sprite['m_RD']['m_VertexData'], old['m_RD']['m_VertexData'])

    def test_unmodified_texture_leaves_sprite_identical(self):
        old=copy.deepcopy(self.sprite)
        self.repair(1.)
        self.assertEqual(self.sprite,old)

class DynamicMapUiTests(unittest.TestCase):
    def test_runtime_assigned_map_sprites_are_ui_even_without_serialized_reference(self):
        fn=getattr(repack, 'is_dynamic_map_ui_sprite', None)
        self.assertTrue(callable(fn), 'dynamic map Image.sprite bindings are missing from UI classification')
        assert fn is not None
        for name in ('map_bsbg','map_blankbg','mainmapbg1','mainmapbg5_b',
                     'map_icon_bsprings','mapicon_frisco'):
            self.assertTrue(fn(name), name)
        for name in ('wallmap','wallmap_perfessor','PC_test_torso','icon_map',
                     'SpriteAtlasTexture-PC-1024x512-fmt2','map_bsbg_decoration'):
            self.assertFalse(fn(name), name)

class RepackSelectionTests(unittest.TestCase):
    def test_keep_id_preserves_exact_texture_and_dependent_sprite_contract(self):
        fn=getattr(repack, 'should_promote_texture', None)
        self.assertTrue(callable(fn), 'repack has no selective atlas preservation')
        assert fn is not None
        self.assertFalse(fn(1024, 11, 1, 123, {123}, 512))
        self.assertTrue(fn(1024, 11, 1, 124, {123}, 512))
        self.assertFalse(fn(256, 9, 1, 124, set(), 512))
        self.assertFalse(fn(1024, 1, 1, 124, set(), 512))

if __name__=='__main__': unittest.main()
