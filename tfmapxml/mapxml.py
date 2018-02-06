import operator
import re
from functools import reduce

GROUND_IDS = {'0': 'Wood',
              '1': 'Ice',
              '2': 'Trampoline',
              '3': 'Lava',
              '4': 'Chocolate',
              '5': 'Earth',
              '6': 'Grass',
              '7': 'Sand',
              '8': 'Cloud',
              '9': 'Water',
              '10': 'Stone',
              '11': 'Snow',
              '12': 'Rectangle',
              '13': 'Circle',
              '14': 'Invisible',
              '15': 'Web', }


class MapXML:
    def __init__(self, xml):
        self.raw_xml = xml
        self._compress()
        self._make_dom()

    def _xml_strip(self, tag):
        tag = re.sub('<', '', tag)
        tag = re.sub('>', '', tag)
        tag = re.sub('/', '', tag)
        return tag

    def _split_xml(self, xml):
        doc = []
        all_tags = (re.findall('<.*?>', xml))
        for tag in all_tags:
            if not re.findall('/>', tag):
                if not re.findall('/', tag):
                    doc.append(f'<{self._xml_strip(tag.strip())}')  # <X>
                else:
                    doc.append(f'{self._xml_strip(tag.strip())}>')  # </X>
            else:
                doc.append(self._xml_strip(tag))
        return doc

    def _split_tags(self, tags):  # split the individual elements into a list of tags
        allattrib = {}
        for attrib in tags:
            splitattrib = []
            tagname = re.sub('\s', '', (''.join(re.findall(r'.*? ', attrib))))  # get the tag name ie JD, S, T etc
            attrib = re.sub('{} '.format(tagname), '', attrib)  # remove the tag name
            rawattrib = (re.split('(.*?=".*?")', attrib))  # get attributes in format X="value"
            for raw in rawattrib:
                if raw != '':  # remove empty spaces found in attributes
                    splitattrib.append(raw)
            for attribs in splitattrib:
                name = re.sub('=', '', ''.join(re.findall('.*?=', attribs)))  # get tag name X of X="value"
                val = ''.join(re.findall('"(.*?)"', attribs))  # get tag value value of X="value"
                allattrib[name] = val  # set the name-value pair based on those above
            allattrib['name'] = tagname  # add the name-value pair to the attributes dict

            return allattrib

    def _merge(self, a, b, path=None):
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self._merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                else:
                    raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
            else:
                a[key] = b[key]
        return a

    def _path_map(self, original_dict, path, value):
        d = {}
        first = True
        for p in reversed(path):
            if first:
                d = {p: value}
                first = False
            else:
                d = {p: d}
        return self._merge(d, original_dict)

    def _make_dom(self):
        xml = self.xml
        parsed = self._split_xml(xml)
        dom = {}
        path = []
        contents = []
        for elem in parsed:
            if re.search('<', elem):
                path.append(self._xml_strip(elem))
                contents = []
            elif re.search('>', elem):
                path.pop()
                contents = []
            else:
                split = self._split_tags([elem])
                contents.append(split)
            if contents:
                attr = {'items': contents}
                dom = self._path_map(dom, path, attr)
        self.dom = dom

    def _compress(self):
        algorithm = [['s\s', ' '],  # remove doublespaces
                     ['> ', '>'],  # remove spaces after closing tag
                     [' <', '<'],  # remove spaces before open_taging tag
                     ['" ', '"'],  # remove spaces in value definitions
                     [',0,', ',,'],  # remove 0 in multivalue definitions
                     [',0\.', ',.'],  # change 0.0 to .0
                     ['"0,', '",'],  # change 0, to ,
                     [',0"', ',"'],  # change ,0 to ,
                     [r' /', r'/'],  # remove spaces before forwardslashes
                     ['\n', ''],  # remove newlines
                     ['\t', ''],  # remove tabs and indents
                     [r',/', r'/'],  # remove commas before forwardslashes
                     [',"', '"'],  # remove empty values at the end of multi value definitions
                     [' >', '>'],  # replace leading whitespace before open_taging tag ends
                     [' />', '/>'],  # replace leading whitespace before closing tag ends
                     ['< ', '<'],  # replace trailing whitespace after open_taging tag starts
                     ['</ ', '</'],  # replace trailing whitespace after closing tag starts
                     ['<VL.*?>', ''],  # remove viprin layer tags
                     ['<!--.*?-->', ''],  # remove comments
                     ['<\?.*?\?>', ''],  # remove processing instructions
                     ['<!\[CDATA\[.*?\]\]>', ''],  # remove CDATA
                     ]
        for replacers in algorithm:
            while len(re.findall(replacers[0], self.raw_xml)) != 0:  # find and replace the items as per the algorithm
                self.raw_xml = re.sub(replacers[0], replacers[1], self.raw_xml)
        self.xml = self.raw_xml.replace('<L/>', '')  # remove the empty joints tag if it exists

    def ground_index(self, index: int):
        try:
            ground = (self.by_path(['C', 'Z', 'S', 'items'])[index])
            return ground
        except (KeyError, IndexError):
            return None

    def by_path(self, path: list):
        try:
            return reduce(operator.getitem, path, self.dom)
        except (ValueError, KeyError):
            return None

    def count_types(self):
        counts = {}
        for element_type, element_name in {'S': 'Grounds', 'D': 'Decorations', 'O': 'Shaman Objects',
                                           'L': 'Joints'}.items():
            try:
                counts[element_name] = len(self.by_path(['C', 'Z', element_type, 'items']))
            except (KeyError, IndexError):
                pass
        return counts

    @property
    def grounds(self):
        ground_count = {}
        for ground in self.by_path(['C', 'Z', 'S', 'items']):
            ground_type = (GROUND_IDS.get(ground['T'], 'Wood'))
            try:
                ground_count[ground_type] += 1
            except KeyError:
                ground_count[ground_type] = 1
        return ground_count

    def _get_total(self, container):
        total = self.by_path(['C', 'Z', container, 'items'])
        return len(total) if total else None

    @property
    def total_joints(self):
        return self._get_total('L')

    @property
    def total_shamobj(self):
        return self._get_total('O')

    @property
    def total_decos(self):
        return self._get_total('D')

    @property
    def total_grounds(self):
        return self._get_total('S')

    @property
    def mouse_spawns(self):
        spawns = []
        for deco in self.by_path(['C', 'Z', 'D', 'items']):
            if deco['name'] == 'DS':
                spawns.append((deco['X'], deco['Y']))
        return spawns

    @property
    def shaman_spawns(self):
        spawns = []
        for deco in self.by_path(['C', 'Z', 'D', 'items']):
            if deco['name'] == 'DC':
                spawns.append((deco['X'], deco['Y']))
        return spawns

    @property
    def get_map_settings(self):
        settings = {}
        named_settings = dict(
            A='Soul Mate',
            aie='Shock Sensitive',
            bh='Upward Cannons',
            C='Collision',
            Ca='Map Border',
            defilante='Defilante',
            G='Wind, Gravity',
            H='Height',
            L='Length',
            mc='Hidden Nails',
            mgoc='Shaman Object Mass',
            N='Night Mode',
            P='Portals',
        )
        for tag in self.by_path(['C', 'items']):
            for name, setting in named_settings.items():
                try:
                    if name == 'G':
                        wind, gravity = (tag[name].split(','))
                        settings['Wind'] = wind
                        settings['Gravity'] = gravity
                    elif tag[name]:
                        settings[named_settings[name]] = tag[name]
                    else:
                        settings[named_settings[name]] = ''
                except KeyError:
                    pass
        return settings
