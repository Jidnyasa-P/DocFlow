# feature_spec.md — shared contract between Colab (Person A) and the offline engine (Person B)
Generated automatically by train.ipynb. If this file and `engine/parser.py`
ever disagree, trust this file and fix the engine.

## Label map (id -> name)
- 0: Title
- 1: Author
- 2: Chapter Heading
- 3: Subheading
- 4: Body Paragraph
- 5: Table
- 6: Figure
- 7: Caption
- 8: Reference
- 9: List

## Feature columns (exact order, exact dtypes -- this is what the model expects)
0. `font_size` (float)
1. `is_bold` (float)
2. `is_italic` (float)
3. `alignment` (float)
4. `indent_left` (float)
5. `indent_first_line` (float)
6. `space_before` (float)
7. `space_after` (float)
8. `line_spacing` (float)
9. `is_all_caps` (float)
10. `starts_with_number` (float)
11. `word_count` (float)
12. `position_ratio_in_doc` (float)
13. `style_name_hash` (float)
14. `has_image` (float)
15. `is_table_element` (float)

## Notes for the offline parser
- `alignment`: 0=left, 1=center, 2=right, 3=justify (see ALIGN_MAP in this notebook)
- `style_name_hash`: index into STYLE_VOCAB = ['Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Title', 'Caption', 'List Paragraph', 'Quote', 'Other']; unknown styles -> 9
- `has_image`: 1 if the paragraph contains an inline `<w:drawing>` element, else 0
- `is_table_element`: 1 if this feature row represents an entire `<w:tbl>` (not a paragraph), else 0
- A `<w:tbl>` produces exactly ONE feature row (not one per cell): font/bold from
  the first populated cell, word_count summed across all cells, alignment/indent/
  spacing fields default to 0
- Paragraphs with no text AND no image are skipped entirely (never a training row)
- scikit-learn version used for training: 1.6.1
