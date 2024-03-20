from unittest import TestCase
from typing import Tuple

from Bio.Align import Alignment, PairwiseAligner
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from palamedes.align import (
    generate_alignment,
    make_variant_base,
    can_merge_variant_blocks,
    merge_variant_blocks,
    generate_seq_records,
    generate_variant_blocks,
)
from palamedes.config import (
    ALT_SEQUENCE_ID,
    GLOBAL_ALIGN_MODE,
    REF_SEQUENCE_ID,
    VARIANT_BASE_MATCH,
    ALIGNMENT_GAP_CHAR,
    VARIANT_BASE_INSERTION,
    VARIANT_BASE_DELETION,
    VARIANT_BASE_MISMATCH,
    MOLECULE_TYPE_PROTEIN,
    MOLECULE_TYPE_ANNOTATION_KEY,
)
from palamedes.models import VariantBlock, Block


class GenerateSeqRecordsTestCase(TestCase):
    def test_generate_seq_records(self):
        ref_seq = "AAA"
        alt_seq = "TTT"

        ref_seq_rec, alt_seq_rec = generate_seq_records(ref_seq, alt_seq)

        self.assertEqual(ref_seq_rec.seq, ref_seq)
        self.assertEqual(ref_seq_rec.id, REF_SEQUENCE_ID)
        self.assertEqual(ref_seq_rec.annotations, {MOLECULE_TYPE_ANNOTATION_KEY: MOLECULE_TYPE_PROTEIN})

        self.assertEqual(alt_seq_rec.seq, alt_seq)
        self.assertEqual(alt_seq_rec.id, ALT_SEQUENCE_ID)
        self.assertEqual(alt_seq_rec.annotations, {MOLECULE_TYPE_ANNOTATION_KEY: MOLECULE_TYPE_PROTEIN})

    def test_generate_seq_records_custom_molecule_type(self):
        ref_seq = "AAA"
        alt_seq = "TTT"
        custom_molecule_type = "dna"

        ref_seq_rec, alt_seq_rec = generate_seq_records(ref_seq, alt_seq, molecule_type=custom_molecule_type)

        self.assertEqual(ref_seq_rec.annotations, {MOLECULE_TYPE_ANNOTATION_KEY: custom_molecule_type})
        self.assertEqual(alt_seq_rec.annotations, {MOLECULE_TYPE_ANNOTATION_KEY: custom_molecule_type})


class MakeVariantBaseTestCase(TestCase):
    def test_make_variant_base_match(self):
        self.assertEqual(make_variant_base("A", "A"), VARIANT_BASE_MATCH)

    def test_make_variant_base_mismatch(self):
        self.assertEqual(make_variant_base("A", "T"), VARIANT_BASE_MISMATCH)

    def test_make_variant_base_deletion(self):
        self.assertEqual(make_variant_base("A", ALIGNMENT_GAP_CHAR), VARIANT_BASE_DELETION)

    def test_make_variant_base_insertion(self):
        self.assertEqual(make_variant_base(ALIGNMENT_GAP_CHAR, "T"), VARIANT_BASE_INSERTION)


class CanMergeVariantBlocksTestCase(TestCase):
    def make_variant_block(self, start: int, end: int, bases: str) -> VariantBlock:
        return VariantBlock(Block(start, end, bases), [], [])

    def test_can_merge_variant_blocks_not_adjacent(self):
        left = self.make_variant_block(0, 4, VARIANT_BASE_DELETION * 4)
        right = self.make_variant_block(6, 8, VARIANT_BASE_MISMATCH * 2)
        self.assertFalse(can_merge_variant_blocks(left, right))

    def test_can_merge_variant_blocks_left_has_match(self):
        left = self.make_variant_block(0, 4, VARIANT_BASE_DELETION * 3 + VARIANT_BASE_MATCH)
        right = self.make_variant_block(4, 6, VARIANT_BASE_MISMATCH * 2)
        self.assertFalse(can_merge_variant_blocks(left, right))

    def test_can_merge_variant_blocks_right_has_match(self):
        left = self.make_variant_block(0, 4, VARIANT_BASE_DELETION * 3 + VARIANT_BASE_MISMATCH)
        right = self.make_variant_block(4, 6, VARIANT_BASE_MISMATCH + VARIANT_BASE_MATCH)
        self.assertFalse(can_merge_variant_blocks(left, right))

    def test_can_merge_variant_blocks_both_have_match(self):
        left = self.make_variant_block(0, 4, VARIANT_BASE_DELETION * 3 + VARIANT_BASE_MATCH)
        right = self.make_variant_block(4, 6, VARIANT_BASE_MISMATCH + VARIANT_BASE_MATCH)
        self.assertFalse(can_merge_variant_blocks(left, right))

    def test_can_merge_variant_blocks_can_merge(self):
        left = self.make_variant_block(0, 4, VARIANT_BASE_DELETION * 3 + VARIANT_BASE_MISMATCH)
        right = self.make_variant_block(4, 6, VARIANT_BASE_MISMATCH + VARIANT_BASE_INSERTION)
        self.assertTrue(can_merge_variant_blocks(left, right))


class MergeVariantBlocksTestCase(TestCase):
    def test_merge_variant_blocks_simple(self):
        """Test merging 2 single base mismatches"""
        left = VariantBlock(
            Block(0, 1, VARIANT_BASE_MISMATCH),
            [Block(0, 1, "A")],
            [Block(0, 1, "T")],
        )
        right = VariantBlock(
            Block(1, 2, VARIANT_BASE_MISMATCH),
            [Block(1, 2, "G")],
            [Block(1, 2, "C")],
        )

        merged = merge_variant_blocks(left, right)

        self.assertEqual(merged.alignment_block.start, left.alignment_block.start)
        self.assertEqual(merged.alignment_block.end, right.alignment_block.end)
        self.assertEqual(merged.alignment_block.bases, VARIANT_BASE_MISMATCH + VARIANT_BASE_MISMATCH)

        self.assertEqual(len(merged.reference_blocks), 1)
        self.assertEqual(merged.reference_blocks[0].start, left.reference_blocks[0].start)
        self.assertEqual(merged.reference_blocks[0].end, right.reference_blocks[0].end)
        self.assertEqual(
            merged.reference_blocks[0].bases, left.reference_blocks[0].bases + right.reference_blocks[0].bases
        )

        self.assertEqual(len(merged.alternate_blocks), 1)
        self.assertEqual(merged.alternate_blocks[0].start, left.alternate_blocks[0].start)
        self.assertEqual(merged.alternate_blocks[0].end, right.alternate_blocks[0].end)
        self.assertEqual(
            merged.alternate_blocks[0].bases, left.alternate_blocks[0].bases + right.alternate_blocks[0].bases
        )

    def test_merge_variant_blocks_complex(self):
        """Test merging 2 complex VariantBlocks based on the following hypothetical alignment:
         T T T -
         - - C G
        0 1 2 3 4 GLOBAL
        0 1 2 3 . REF
        . . 0 1 2 ALT
        The left side will already have ddm, we are merging in the insertion for the test.
        """
        left = VariantBlock(
            Block(0, 3, "".join([VARIANT_BASE_DELETION, VARIANT_BASE_DELETION, VARIANT_BASE_MISMATCH])),
            [Block(0, 3, "TTT")],
            [Block(0, 1, "C")],
        )
        right = VariantBlock(
            Block(3, 4, VARIANT_BASE_INSERTION),
            [],
            [Block(1, 2, "G")],
        )

        merged = merge_variant_blocks(left, right)

        self.assertEqual(merged.alignment_block.start, left.alignment_block.start)
        self.assertEqual(merged.alignment_block.end, right.alignment_block.end)
        self.assertEqual(
            merged.alignment_block.bases,
            "".join([VARIANT_BASE_DELETION, VARIANT_BASE_DELETION, VARIANT_BASE_MISMATCH, VARIANT_BASE_INSERTION]),
        )

        # there is no right ref block, so everything is on the left one
        self.assertEqual(len(merged.reference_blocks), 1)
        self.assertEqual(merged.reference_blocks[0], left.reference_blocks[0])

        self.assertEqual(len(merged.alternate_blocks), 1)
        self.assertEqual(merged.alternate_blocks[0].start, left.alternate_blocks[0].start)
        self.assertEqual(merged.alternate_blocks[0].end, right.alternate_blocks[0].end)
        self.assertEqual(
            merged.alternate_blocks[0].bases, left.alternate_blocks[0].bases + right.alternate_blocks[0].bases
        )


class GenerateAlignmentTestCase(TestCase):
    def make_seq_records(
        self, ref_seq: str, alt_seq: str, molecule_type: str = MOLECULE_TYPE_PROTEIN
    ) -> Tuple[SeqRecord, SeqRecord]:
        ref = SeqRecord(Seq(ref_seq), id=REF_SEQUENCE_ID, annotations={MOLECULE_TYPE_ANNOTATION_KEY: molecule_type})
        alt = SeqRecord(Seq(alt_seq), id=ALT_SEQUENCE_ID, annotations={MOLECULE_TYPE_ANNOTATION_KEY: molecule_type})
        return ref, alt

    def test_generate_alignment_missing_molecule_type_error(self):
        ref, alt = self.make_seq_records("A", "A", molecule_type="foobar")
        del ref.annotations[MOLECULE_TYPE_ANNOTATION_KEY]
        with self.assertRaisesRegex(ValueError, "got: None"):
            generate_alignment(ref, alt)

    def test_generate_alignment_wrong_molecule_type_error(self):
        ref, alt = self.make_seq_records("A", "A", molecule_type="foobar")

        with self.assertRaisesRegex(ValueError, f"expected: {MOLECULE_TYPE_PROTEIN}"):
            generate_alignment(ref, alt)

    def test_generate_alignment_custom_aligner_mode_error(self):
        local_mode = "local"
        custom_aligner = PairwiseAligner(mode=local_mode)
        ref, alt = self.make_seq_records("A", "T")
        with self.assertRaisesRegex(ValueError, f"got: {local_mode}"):
            generate_alignment(ref, alt, aligner=custom_aligner)

    def test_generate_alignment(self):
        ref, alt = self.make_seq_records("A", "T")

        alignment = generate_alignment(ref, alt)

        self.assertTrue(isinstance(alignment, Alignment))
        self.assertIs(alignment.target, ref)
        self.assertIs(alignment.query, alt)

    def test_generate_alignment_custom_aligner(self):
        ref, alt = self.make_seq_records("A", "A")

        custom_match_score = 10_000
        custom_aligner = PairwiseAligner(mode=GLOBAL_ALIGN_MODE, match_score=custom_match_score)

        alignment = generate_alignment(ref, alt, aligner=custom_aligner)
        self.assertTrue(alignment.score, custom_match_score)


class GenerateVariantBlocksTestCase(TestCase):
    def make_alignment(self, ref_aligned_bases: str, alt_aligned_bases: str) -> Alignment:
        coords = Alignment.infer_coordinates([ref_aligned_bases, alt_aligned_bases])
        return Alignment(
            [ref_aligned_bases.replace(ALIGNMENT_GAP_CHAR, ""), alt_aligned_bases.replace(ALIGNMENT_GAP_CHAR, "")],
            coords,
        )

    def test_generate_variant_blocks_all_matches(self):
        alignment = self.make_alignment("A" * 5, "A" * 5)
        self.assertEqual(generate_variant_blocks(alignment), [])

    def test_generate_variant_blocks_all_matches_single_mismatch(self):
        alignment = self.make_alignment("ACT", "AGT")
        variant_blocks = generate_variant_blocks(alignment)

        self.assertEqual(len(variant_blocks), 1)
        self.assertEqual(variant_blocks[0].alignment_block, Block(1, 2, VARIANT_BASE_MISMATCH))
        self.assertEqual(variant_blocks[0].reference_blocks, [Block(1, 2, "C")])
        self.assertEqual(variant_blocks[0].alternate_blocks, [Block(1, 2, "G")])

    def test_generate_variant_blocks_merging(self):
        """
        Test an alignment with a 3 position variant in order, deletion -> mismatch -> insertion
            A T C - T
            A - G A T
           0 1 2 3 4 5 GLOBAL
           0 1 2 3 . 4 REF
           0 . 1 2 3 4 ALT
        """
        alignment = self.make_alignment(
            "ATC-T",
            "A-GAT",
        )
        variant_blocks = generate_variant_blocks(alignment)

        self.assertEqual(len(variant_blocks), 1)
        self.assertEqual(
            variant_blocks[0].alignment_block,
            Block(1, 4, "".join([VARIANT_BASE_DELETION, VARIANT_BASE_MISMATCH, VARIANT_BASE_INSERTION])),
        )
        self.assertEqual(variant_blocks[0].reference_blocks, [Block(1, 3, "TC")])
        self.assertEqual(variant_blocks[0].alternate_blocks, [Block(1, 3, "GA")])

    def test_generate_variant_blocks_complex(self):
        """
        Test an alignment with a number of variants, some merged and some not
            A T C T - - T
            A - C G A A T
           0 1 2 3 4 5 6 7 GLOBAL
           0 1 2 3 4 . . 6 REF
           0 . 1 2 3 4 5 6 ALT

        The full "variant bases" would be: MdMmiiM
        """
        alignment = self.make_alignment(
            "ATCT--T",
            "A-CGAAT",
        )
        variant_blocks = generate_variant_blocks(alignment)

        # mii gets merged so 2 total
        self.assertEqual(len(variant_blocks), 2)
        self.assertEqual(
            variant_blocks[0].alignment_block,
            Block(1, 2, VARIANT_BASE_DELETION),
        )
        self.assertEqual(variant_blocks[0].reference_blocks, [Block(1, 2, "T")])
        self.assertEqual(variant_blocks[0].alternate_blocks, [])

        self.assertEqual(
            variant_blocks[1].alignment_block,
            Block(3, 6, "".join([VARIANT_BASE_MISMATCH, VARIANT_BASE_INSERTION, VARIANT_BASE_INSERTION])),
        )
        self.assertEqual(variant_blocks[1].reference_blocks, [Block(3, 4, "T")])
        self.assertEqual(variant_blocks[1].alternate_blocks, [Block(2, 5, "GAA")])
