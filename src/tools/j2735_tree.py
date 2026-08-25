#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys

import j2735_202409
from pycrate_asn1rt.refobj import ASN1RefType

# ASN.1 type categories
CONSTRUCTED = ('SEQUENCE', 'SET', 'CHOICE')
LIST_TYPES = ('SEQUENCE OF', 'SET OF')
NAMED_VALUE_TYPES = ('ENUMERATED', 'BIT STRING', 'INTEGER')

# Presence classes used throughout the walker and the renderers.
MANDATORY = 'mandatory'
OPTIONAL = 'optional'
ALTERNATIVE = 'alternative'  # CHOICE alternative
ITEM = 'item'                # element of a SEQUENCE OF / SET OF
OPEN = 'open'                # alternative of an open type table
NAMED_VALUE = 'value'        # member of an ENUMERATED / BIT STRING / named INTEGER

MARKERS = {
    MANDATORY: 'M',
    OPTIONAL: 'O',
    ALTERNATIVE: '|',
    ITEM: '*',
    OPEN: '~',
    NAMED_VALUE: '=',
}

LEGEND = [
    ('M', 'mandatory field'),
    ('O', 'OPTIONAL field'),
    ('|', 'CHOICE alternative (exactly one is present)'),
    ('*', 'repeated element of a SEQUENCE OF / SET OF'),
    ('~', 'open type alternative, selected by the sibling id field'),
    ('=', 'named value of an ENUMERATED / BIT STRING / named INTEGER'),
    ('(ext)', 'extension addition (added after the ASN.1 "..." marker)'),
    ('(...)', 'the type itself is extensible'),
]

# Common acronyms for the J2735 messages, so `BSM` works as well as `BasicSafetyMessage`. Keys are matched case-insensitively.
ALIASES = {
    'BSM': 'BasicSafetyMessage',
    'MAP': 'MapData',
    'SPAT': 'SPAT',
    'CSR': 'CommonSafetyRequest',
    'EVA': 'EmergencyVehicleAlert',
    'ICA': 'IntersectionCollision',
    'NMEA': 'NMEAcorrections',
    'PDM': 'ProbeDataManagement',
    'PVD': 'ProbeVehicleData',
    'RSA': 'RoadSideAlert',
    'RTCM': 'RTCMcorrections',
    'SRM': 'SignalRequestMessage',
    'SSM': 'SignalStatusMessage',
    'TIM': 'TravelerInformation',
    'PSM': 'PersonalSafetyMessage',
    'PSM2': 'PersonalSafetyMessage2',
    'RSM': 'RoadSafetyMessage',
    'RWM': 'RoadWeatherMessage',
    'PDC': 'ProbeDataConfigMessage',
    'PDR': 'ProbeDataReportMessage',
    'TAM': 'TollAdvertisementMessage',
    'TUM': 'TollUsageMessage',
    'TumAck': 'TollUsageAckMessage',
    'CCM': 'CooperativeControlMessage',
    'SDSM': 'SensorDataSharingMessage',
    'MSCM': 'ManeuverSharingAndCoordinatingMessage',
    'RGA': 'RoadGeometryAndAttributes',
    'TSPaT': 'TrafficSignalPhaseAndTiming',
    'SCPR': 'SignalControlAndPrioritizationRequest',
    'SCPS': 'SignalControlAndPrioritizationStatus',
    'RUCCM': 'RoadUserChargingConfigMessage',
    'RUCRM': 'RoadUserChargingReportMessage',
    'TLSM': 'TrafficLightStatusMessage',
}

COLORS = {
    MANDATORY: '\033[0m',
    OPTIONAL: '\033[33m',
    ALTERNATIVE: '\033[35m',
    ITEM: '\033[32m',
    OPEN: '\033[35m',
    NAMED_VALUE: '\033[2m',
}
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'

def message_registry() -> dict:
    """Map message name to (messageId, ASN.1 object) from the MessageFrame table."""
    frame = j2735_202409.MessageFrame.MessageFrame
    table = frame._cont['value']._const_tab
    registry = {}
    for entry in table._val.root:
        ref = entry['Type']._typeref
        name = ref.called[1] if isinstance(ref, ASN1RefType) else entry['Type']._name
        obj = entry['Type']
        if isinstance(ref, ASN1RefType):
            module = getattr(j2735_202409, ref.called[0], None)
            obj = getattr(module, ref.called[1], obj) if module else obj
        registry[name] = (entry['id'], obj)
    return registry

def resolve_selection(names, registry):
    """Resolve user-provided names/acronyms to verified message names."""
    by_lower = {n.lower(): n for n in registry}
    alias_lower = {a.lower(): full for a, full in ALIASES.items()}

    selected, unknown = [], []
    for entry in names:
        key = entry.strip()
        hit = (by_lower.get(key.lower())
               or by_lower.get(alias_lower.get(key.lower(), '').lower()))
        if hit and hit not in selected:
            selected.append(hit)
        elif not hit:
            unknown.append(entry)
    return selected, unknown

def type_ref_name(obj):
    """Name of the referenced ASN.1 type."""
    ref = obj._typeref
    if isinstance(ref, ASN1RefType):
        return ref.called[1]
    return None

def type_identity(obj):
    """Stable 'Module.Type' id used to detect recursion."""
    ref = obj._typeref
    if isinstance(ref, ASN1RefType):
        return '%s.%s' % ref.called
    return None

def format_set(aset):
    """Format an ASN1Set of ints / ASN1RangeInt as `0..127`, `1|3|5`, etc."""
    parts = []
    for item in (aset.root or []):
        lb, ub = getattr(item, 'lb', None), getattr(item, 'ub', None)
        if lb is None and ub is None:
            parts.append(str(item))
        else:
            lo = 'MIN' if lb is None else str(lb)
            hi = 'MAX' if ub is None else str(ub)
            parts.append(lo if lo == hi else '%s..%s' % (lo, hi))
    text = '|'.join(parts) if parts else ''
    if aset.ext is not None:
        text = (text + ', ...') if text else '...'
    return text

def constraints_of(obj):
    """Human-readable constraint string, e.g. `(0..8191)` or `(SIZE(1..8))`."""
    try:
        const = obj.get_const()
    except Exception:
        return None
    parts = []
    if 'sz' in const:
        text = format_set(const['sz'])
        if text:
            parts.append('SIZE(%s)' % text)
    if 'val' in const:
        text = format_set(const['val'])
        if text:
            parts.append(text)
    for key, val in const.items():
        if key not in ('sz', 'val') and not key.startswith('tab'):
            parts.append('%s=%s' % (key, val))
    return ', '.join(parts) if parts else None

def named_values(obj):
    """Named values of an ENUMERATED / BIT STRING / named INTEGER, as a list."""
    if obj.TYPE not in NAMED_VALUE_TYPES:
        return None
    cont = obj._cont
    if cont is None or not hasattr(cont, 'items') or not len(cont):
        return None
    return [(name, value) for name, value in cont.items()]

def open_type_alternatives(obj):
    """Alternatives of an open type, read from its table constraint."""
    table = getattr(obj, '_const_tab', None)
    if table is None or table._val is None:
        return []
    id_key = (table._lut or {}).get('__key__', 'id')
    type_key = getattr(obj, '_const_tab_id', 'Type')
    out = []
    for entry in (table._val.root or []):
        target = entry.get(type_key)
        if target is None:
            continue
        ref = target._typeref
        if isinstance(ref, ASN1RefType):
            module = getattr(j2735_202409, ref.called[0], None)
            resolved = getattr(module, ref.called[1], target) if module else target
        else:
            resolved = target
        out.append((entry.get(id_key), resolved))
    return out

def build_node(obj, opts, field=None, presence=MANDATORY, is_ext=False, selector=None, depth=0, stack=()):
    """Recursively describe an ASN.1 object as a dict."""
    node = {
        'field': field,
        'type': type_ref_name(obj),
        'asn1_type': obj.TYPE,
        'presence': presence,
        'extension_addition': is_ext,
        'extensible': obj._ext is not None,
        'constraints': constraints_of(obj) if opts.constraints else None,
        'selector': selector,
        'depth': depth,
        'children': [],
        'truncated': None,
    }

    values = named_values(obj)
    if values and opts.values != 'none':
        node['values'] = values

    identity = type_identity(obj)
    if identity and identity in stack:
        node['truncated'] = 'recursive'
        return node
    next_stack = stack + (identity,) if identity else stack

    if obj.TYPE in CONSTRUCTED:
        cont = obj._cont or {}
        ext_names = set(obj._ext or ())
        for name, member in cont.items():
            if obj.TYPE == 'CHOICE':
                member_presence = ALTERNATIVE
            elif member._opt:
                member_presence = OPTIONAL
            elif member._def:
                raise ValueError("Default value detected! Default values did not previously exist and are not handled.")
            else:
                member_presence = MANDATORY
            node['children'].append(build_node(member, opts, field=name, presence=member_presence,
                                               is_ext=name in ext_names, depth=depth + 1, stack=next_stack))

    elif obj.TYPE in LIST_TYPES:
        item = obj._cont
        if item is not None:
            node['children'].append(build_node(item, opts, field='_item_', presence=ITEM,
                                               depth=depth + 1, stack=next_stack))

    elif obj.TYPE == 'OPEN_TYPE' and opts.open_types:
        for key, target in open_type_alternatives(obj):
            node['children'].append(build_node(target, opts, field=type_ref_name(target) or target._name,
                                               presence=OPEN, selector=key, depth=depth + 1, stack=next_stack))

    if values and opts.values == 'full':
        for name, value in values:
            node['children'].append({'field': name, 'type': None, 'asn1_type': 'value',
                                     'presence': NAMED_VALUE, 'extension_addition': False,
                                     'extensible': False, 'constraints': None,'selector': value,
                                     'depth': depth + 1, 'children': [], 'truncated': None,
                                     })

    return node

def build_message_tree(name, message_id, obj, opts):
    node = build_node(obj, opts, field=name)
    node['message'] = name
    node['message_id'] = message_id
    if obj.TYPE == 'NULL' and obj._cont is None:
        node['note'] = 'reserved: not defined in this revision'
    return node

def filter_presence(node, wanted):
    """Prune to fields matching `wanted`."""
    kept = [c for c in (filter_presence(c, wanted) for c in node['children']) if c]
    node = dict(node, children=kept)
    if node['presence'] == wanted or kept or 'message' in node:
        return node
    return None

def describe_type(node, opts):
    """`BSMcoreData [SEQUENCE] (SIZE(1..8))` style type description."""
    parts = []
    if node['type'] and node['type'] != node['asn1_type']:
        parts.append(node['type'])
    parts.append(node['asn1_type'] if not parts else '[%s]' % node['asn1_type'])
    if node['extensible']:
        parts.append('(...)')
    if node['constraints']:
        parts.append('(%s)' % node['constraints'])
    if node.get('values') and opts.values == 'inline':
        shown = node['values'][:]
        text = ', '.join('%s(%s)' % (n, v) for n, v in shown)
        if len(node['values']) > len(shown):
            text += ', ... +%d' % (len(node['values']) - len(shown))
        parts.append('{%s}' % text)
    return ' '.join(parts)

def node_label(node, opts):
    marker = MARKERS.get(node['presence'], ' ')
    field = node['field'] or ''
    if node['presence'] == ITEM and node['asn1_type'] != 'value':
        field = 'each element'
    if node['presence'] == OPEN and node['selector'] is not None:
        field = '%s = %s' % (node['selector'], field)
    if node['asn1_type'] == 'value':  # expanded enum/bitstring member
        body = '%s = %s' % (field, node['selector'])
    else:
        body = '%s : %s' % (field, describe_type(node, opts))
    suffix = ''
    if node['extension_addition']:
        suffix += ' (ext)'
    if node['truncated'] == 'recursive':
        suffix += ' -> recursive, see above'
    tint = COLORS.get(node['presence'], '')
    return '%s%s%s %s%s%s' % (BOLD, marker, RESET, tint, body, RESET) + \
            (DIM + suffix + RESET if suffix else '')

def render_tree(roots, opts, out):
    glyphs = ('├── ', '└── ', '│   ', '    ')

    def walk(node, prefix, last):
        connector = glyphs[1] if last else glyphs[0]
        out.write(prefix + connector + node_label(node, opts) + '\n')
        child_prefix = prefix + (glyphs[3] if last else glyphs[2])
        for i, child in enumerate(node['children']):
            walk(child, child_prefix, i == len(node['children']) - 1)

    out.write(BOLD + 'Legend:\n' + RESET)
    for marker, text in LEGEND:
        out.write('  %-6s %s\n' % (marker, text))
    out.write('\n')

    for root in roots:
        header = '%s  [messageId %s]' % (root['message'], root['message_id'])
        out.write((BOLD + header + RESET) + '\n')
        if root.get('note'):
            out.write('  %s\n' % root['note'])
        out.write('  %s\n' % describe_type(root, opts))
        for i, child in enumerate(root['children']):
            walk(child, '  ', i == len(root['children']) - 1)
        out.write('\n')

def render_markdown(roots, opts, out):
    out.write('**Legend:**\n')
    for marker, text in LEGEND:
        out.write('- `%s` %s\n' % (marker, text))
    out.write('\n')

    for root in roots:
        out.write('## %s (messageId %s)\n\n' % (root['message'], root['message_id']))
        if root.get('note'):
            out.write('> %s\n\n' % root['note'])
        out.write('`%s`\n\n' % describe_type(root, opts))

        def walk(node, level):
            marker = MARKERS.get(node['presence'], ' ')
            field = node['field'] or ''
            if node['presence'] == ITEM and node['asn1_type'] != 'value':
                field = '_each element_'
            if node['asn1_type'] == 'value':
                body = '`%s` = %s' % (field, node['selector'])
            else:
                body = '**%s** — `%s`' % (field, describe_type(node, opts))
            extra = ''
            if node['extension_addition']:
                extra += ' _(ext)_'
            if node['truncated'] == 'recursive':
                extra += ' _(recursive)_'
            out.write('%s- `%s` %s%s\n' % ('  ' * level, marker, body, extra))
            for child in node['children']:
                walk(child, level + 1)

        for child in root['children']:
            walk(child, 0)
        out.write('\n')

def render_csv(roots, out):
    def max_depth(node):
        return max([node['depth']] + [max_depth(c) for c in node['children']])

    deepest = max((max_depth(root) for root in roots), default=0)
    levels = ['level_%d' % i for i in range(deepest + 1)]

    def label(node):
        if 'message' in node:  # root row
            return node['message']
        if node['presence'] == ITEM:
            return '[each element]'
        if node['presence'] == OPEN and node['selector'] is not None:
            return '[%s] %s' % (node['selector'], node['field'] or '')
        return node['field'] or ''

    def note(node):
        return 'recursive' if node['truncated'] == 'recursive' else ''

    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(levels + ['type', 'asn1_type', 'presence', 'selector', 'constraints',
                              'extension_addition', 'extensible', 'note'])

    def walk(node):
        indent = [''] * len(levels)
        indent[node['depth']] = label(node)
        writer.writerow(
            indent + [node['type'] or '', node['asn1_type'], node['presence'],
             '' if node['selector'] is None else node['selector'],
             node['constraints'] or '',
             node['extension_addition'], node['extensible'], note(node)])
        for child in node['children']:
            walk(child)

    for root in roots:
        walk(root)

def render_json(roots, out):
    def clean(node):
        data = {k: v for k, v in node.items() if k != 'children'}
        data = {k: v for k, v in data.items()
                if v is not None and v is not False}
        if node['children']:
            data['children'] = [clean(c) for c in node['children']]
        return data
    payload = [clean(r) for r in roots]
    json.dump(payload, out, indent=2, default=str)
    out.write('\n')

def print_message_list(registry, out):
    reverse = {}
    for alias, full in ALIASES.items():
        reverse.setdefault(full, alias)
    out.write('%-6s %-42s %-8s %s\n' % ('ID', 'MESSAGE', 'ALIAS', 'TOP-LEVEL TYPE'))
    for name, (mid, obj) in sorted(registry.items(), key=lambda kv: kv[1][0]):
        note = obj.TYPE
        if obj.TYPE == 'NULL' and obj._cont is None:
            note = 'NULL (reserved in this revision)'
        out.write('%-6s %-42s %-8s %s\n' % (mid, name, reverse.get(name, ''), note))

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description='Render the J2735 (2024-09) V2X message structures as a tree.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('messages', nargs='*',
                        help='messages to render by name, acronym (BSM, SDSM, ...); default is every message')
    parser.add_argument('-l', '--list', action='store_true',
                        help='list the available messages and exit')
    parser.add_argument('-f', '--format', default='tree',
                        choices=['tree', 'markdown', 'json', 'csv'],
                        help='output format (default: tree)')
    parser.add_argument('-o', '--output', metavar='FILE',
                        help='write to FILE instead of stdout')
    parser.add_argument('-p', '--presence', default='all',
                        choices=['all', 'mandatory', 'optional'],
                        help='only show fields with this presence (default: all)')
    parser.add_argument('--values', default='inline',
                        choices=['none', 'inline', 'full'],
                        help='how to show ENUMERATED / BIT STRING members (default: inline)')
    parser.add_argument('--no-constraints', dest='constraints', action='store_false',
                        help='hide size and value constraints')
    parser.add_argument('--no-open-types', dest='open_types', action='store_false',
                        help='do not expand open type / regional extension tables')
    return parser.parse_args(argv)

def main(argv=None):
    opts = parse_args(argv if argv is not None else sys.argv[1:])
    registry = message_registry()

    stream = open(opts.output, 'w') if opts.output else sys.stdout
    try:
        if opts.list:
            print_message_list(registry, stream)
            return 0

        if opts.messages:
            selected, unknown = resolve_selection(opts.messages, registry)
            if unknown:
                sys.stderr.write('unknown message(s): %s\n' % ', '.join(unknown))
                sys.stderr.write('run with --list to see the available messages\n')
                return 2
        else:
            selected = [n for n, _ in sorted(registry.items(), key=lambda kv: kv[1][0])]

        roots = []
        for name in selected:
            message_id, obj = registry[name]
            root = build_message_tree(name, message_id, obj, opts)
            if opts.presence != 'all':
                root = filter_presence(root, opts.presence)
            roots.append(root)

        if opts.format == 'tree':
            render_tree(roots, opts, stream)
        elif opts.format == 'markdown':
            render_markdown(roots, opts, stream)
        elif opts.format == 'csv':
            render_csv(roots, stream)
        elif opts.format == 'json':
            render_json(roots, stream)
        return 0
    except BrokenPipeError:
        # Redirect the remaining output so the interpreter doesn't warn at shutdown
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    finally:
        if opts.output:
            stream.close()

if __name__ == '__main__':
    sys.exit(main())
