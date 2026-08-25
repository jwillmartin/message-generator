# J2735 Message Tree

`j2735_tree.py` renders the structure of every SAE J2735 (2024-09) V2X message as a
tree, showing each field's type, its constraints, and whether it is `MANDATORY` or
`OPTIONAL`.

The list of messages and their `messageId` values is read from the `MessageFrame`
information object set, so nothing is hard-coded.

## Usage

```bash
./j2735_tree.py --list                  # every message, with its messageId and acronym
./j2735_tree.py BSM                     # one message, fully expanded
./j2735_tree.py SRM SignalStatusMessage # several, by acronym or name
./j2735_tree.py                         # every message
```

Messages can be named in full (`SensorDataSharingMessage`) or by acronym (`SDSM`). All are case-insensitive.

## Markers

```
M      mandatory field
O      OPTIONAL field
|      CHOICE alternative (exactly one is present)
*      repeated element of a SEQUENCE OF / SET OF
~      open type alternative, selected by the sibling id field
=      named value of an ENUMERATED / BIT STRING / named INTEGER
(ext)  extension addition (added after the ASN.1 "..." marker)
(...)  the type itself is extensible
```

## Output formats

`--format` selects the renderer:

| Format     | Use it for |
|------------|------------|
| `tree`     | default; Unicode box drawing, colorized on a TTY |
| `markdown` | nested bullet list, for documentation |
| `json`     | machine-readable, for tooling |
| `csv`      | one row per field, indented across `level_N` columns, for spreadsheets |

```bash
./j2735_tree.py --format markdown -o tree.md
./j2735_tree.py --format csv -o tree.csv
```

### CSV layout

The CSV reads as a tree. A field at depth N puts its name in column `level_N`
and leaves the other level columns empty, so it reads as a tree in a spreadsheet:

| level_0 | level_1 | level_2 | type | asn1_type | presence |
|---|---|---|---|---|---|
| BasicSafetyMessage | | | | SEQUENCE | mandatory |
| | coreData | | BSMcoreData | SEQUENCE | mandatory |
| | | msgCnt | MsgCount | INTEGER | mandatory |
| | | id | TemporaryID | OCTET STRING | mandatory |

The remaining columns are `selector`, `constraints`, `default`,
`extension_addition`, `extensible`, and `note` (`recursive`).

## Other options

| Option | Effect |
|--------|--------|
| `-p, --presence {all,mandatory,optional}` | show only fields with this presence, keeping their parents for context |
| `--values {none,inline,full}` | how to show `ENUMERATED` / `BIT STRING` members (default `inline`) |
| `--no-constraints` | hide size and value ranges |
| `--no-open-types` | do not expand open type / regional extension tables |
| `-o, --output FILE` | write to a file instead of stdout |

## Notes

- **Recursion.** Types such as `RegionalExtension` can nest into themselves. A
  repeat of a type already on the current path is marked `recursive` rather than
  expanded again, so the walk always terminates.
- **Open types.** `partII-Value`, `regExtValue`, and similar fields are `OPEN_TYPE`.
  Their alternatives are read from the ASN.1 table constraint and listed with the id 
  that selects each one. Some regional extension tables are empty and expand to nothing.
- **Reserved messages.** A few `messageId` values (43-47) are placeholders in this
  revision and resolve to `NULL`; they are reported as reserved.
