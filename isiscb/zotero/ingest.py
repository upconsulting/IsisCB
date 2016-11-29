from isisdata.models import *
from zotero.models import *
from zotero.parse import ZoteroIngest

import re, os, csv, jsonpickle
from pprint import pprint


DOCUMENT_TYPE_DEFAULT = DraftCitation.ARTICLE
DOCUMENT_TYPES = {
    'journalarticle': DraftCitation.ARTICLE,
    'article': DraftCitation.ARTICLE,
    'book': Citation.BOOK,
    'thesis': DraftCitation.THESIS,
    'booksection': DraftCitation.CHAPTER,
    'webpage': DraftCitation.WEBSITE,
}


# These fields can be mapped directly onto the DraftCitation model.
CITATION_FIELDS = [
    'title', 'abstract', 'publication_date', 'type_controlled',
    'type_controlled', 'volume', 'issue', 'extent'
]

# These fields can be mapped directly onto the DraftAuthority model.
AUTHORITY_FIELDS = [
    'name', 'name_first', 'name_last'
]


GENERIC_ACRELATIONS = [
    ('authors', Authority.PERSON, ACRelation.AUTHOR),
    ('editors', Authority.PERSON, ACRelation.EDITOR),
    ('series_editors', Authority.PERSON, ACRelation.EDITOR),
    ('contributors', Authority.PERSON, ACRelation.CONTRIBUTOR),
    ('translators', Authority.PERSON, ACRelation.TRANSLATOR),
]


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../AuthorityIDmap.tab'), 'rU') as f:
    reader = csv.reader(f, delimiter='\t')
    SUBJECT_ID_MAP = {int(row[1]): row[0] for row in reader}


class IngestManager(object):
    """
    Orchestrates the ingestion of data into the Zotero app.
    """

    def __init__(self, parser, accession):
        self.parser = parser
        self.accession = accession
        self.draft_citation_map = {}
        self.draft_citations = []
        self.unique = set()
        self.draft_citation_hash = {}

    HASH_KEYS = ['title', 'type_controlled']

    @staticmethod
    def hash(entry):
        return repr([entry.get(k, u'') for k in IngestManager.HASH_KEYS])

    def _update_or_create_draft_citation(self, data, linkeddata, ref=None, original=None):
        _base_key = (data.get('title'), data.get('type_controlled'), 'None', 'None')
        _partof_key = (data.get('title'), data.get('type_controlled'), repr(ref), 'None')
        _linkeddata_key = (data.get('title'), data.get('type_controlled'), 'None', repr(linkeddata))
        _combined_key = (data.get('title'), data.get('type_controlled'), repr(ref), repr(linkeddata))

        draft_citation = None
        for _key in [_combined_key, _linkeddata_key, _partof_key, _base_key]:
            draft_citation = self.draft_citation_hash.pop(_key, None)
            if draft_citation:
                updated = False
                for key, value in data.iteritems():
                    if value and getattr(draft_citation, key, None) != value:
                        setattr(draft_citation, key, value)
                        updated = True
                if updated:
                    draft_citation.source_data = jsonpickle.dumps(original)
                draft_citation.save()
                break
        if not draft_citation:
            draft_citation = DraftCitation.objects.create(source_data=repr(original), **data)
        self.draft_citation_hash[_combined_key] = draft_citation
        return self.draft_citation_hash[_combined_key]

    @staticmethod
    def resolve(d, p):
        """
        Create an :class:`.InstanceResolutionEvent` for draft ``d`` to
        production instance ``p``.
        """
        d.processed = True
        d.save()
        return InstanceResolutionEvent.objects.create(for_instance=d,
                                                      to_instance=p)

    @staticmethod
    def _get(entry, key, default=None):
        """
        Get ``key`` from ``entry``, and join values into a single object.

        Parameters
        ----------
        entry : dict
        key : str
        default : object

        Returns
        -------
        object
        """
        value = entry.get(key, default)

        if type(value) is list:
            return value[0] if len(value) == 1 else u'; '.join(value)
        return value

    @staticmethod
    def _get_pages_data(entry):
        """
        Generate data for :prop:`.DraftCitation.page_start`\, :prop:`.page_end`\,
        and :prop:`.pages_free_text`\.

        Parameters
        ----------
        entry : dict

        Returns
        -------
        dict
        """
        value = IngestManager._get(entry, 'pages', None)
        if type(value) not in [tuple, list]:
            page_start, page_end, pages_free_text = value, None, value
        else:
            try:    # ISISCB-395: Skip malformed page numbers.
                page_start, page_end = value
                pages_free_text = u'-'.join(map(unicode, list(value)))
            except ValueError:    # free_text only.
                page_start, page_end, pages_free_text = value[0], None, value[0]
        return {
            'page_start': page_start,
            'page_end': page_end,
            'pages_free_text': pages_free_text,
        }

    @staticmethod
    def _get_dtype(entry, default=DOCUMENT_TYPE_DEFAULT):
        """
        Generate data for :prop:`.DraftCitation.type_controlled`\.

        Parameters
        ----------
        entry : dict

        Returns
        -------
        dict
        """
        _key = entry.get('type_controlled')
        if type(_key) is list:
            _key = _key[0]
        if _key:
            _key = _key.lower()

        return {
            'type_controlled': DOCUMENT_TYPES.get(_key, default)
        }

    @staticmethod
    def find_extra_data(raw):
        """
        Parses strings for explicit key/value data in curly braces, and returns
        the data as a list of (key, value) tuples.

        Parameters
        ----------
        raw : str

        Returns
        -------
        list
        """
        return [tuple(match.split(':')) for match in re.findall(ur'\{([^\{]+)\}', raw)]

    @staticmethod
    def _update_field(key, value):
        def _call(obj):
            setattr(obj, key, value)
            return obj
        return _call

    @staticmethod
    def _set_viaf_linkeddata(key, value):
        if not value.startswith('http'):
            value = u'http://viaf.org/viaf/%s' % value
        def _update_viaf_linkeddata(obj):
            DraftAuthorityLinkedData.objects.create(
                authority=obj,
                name=key,
                value=value,
                part_of=obj.part_of
            )
            obj.refresh_from_db()
            return obj
        return _update_viaf_linkeddata

    EXTRA_DATA_HANDLERS = {
        'name': _update_field.__func__,
        'viaf': _set_viaf_linkeddata.__func__,
    }

    @staticmethod
    def apply_extra_data(data):
        """
        Handles parsed key/value pairs and returns a callable that will update
        a model instance accordingly. The callable should return the instance
        that was passed.
        """

        def _update(obj):
            for key, value in data:
                handler = IngestManager.EXTRA_DATA_HANDLERS.get(key, None)
                if handler:
                    obj = handler(key, value)(obj)
            if hasattr(obj, 'save'):
                obj.save()
            return obj
        return _update


    @staticmethod
    def generate_language_relations(entry, draft_citation):
        """
        If language data is available, attempt to populate
        :prop:`.DraftCitation.language`\.
        """
        literal = IngestManager._get(entry, 'language')
        if not literal:
            return
        try:
            language = Language.objects.get(id=literal)
        except Language.DoesNotExist:
            try:
                language = Language.objects.get(name=literal)
            except Language.DoesNotExist:
                return

        draft_citation.language = language
        draft_citation.save()

    @staticmethod
    def generate_citation_linkeddata(entry, draft_citation):
        """
        Generate new :class:`.DraftCitationLinkedData` instances from
        field-data.

        Parameters
        ----------
        entry : dict
        draft_citation : :class:`.DraftCitation`

        Returns
        -------
        list
            A list of :class:`.DraftCitationLinkedData` instances.
        """

        _cast = lambda datum: DraftCitationLinkedData.objects.create(
            name = datum[0].upper(),
            value = datum[1],
            citation = draft_citation,
            part_of = draft_citation.part_of,
        )
        return map(_cast, entry.get('linkeddata', []))

    @staticmethod
    def generate_authority_linkeddata(entry, draft_authority):
        """
        Generate new :class:`.DraftAuthorityLinkedData` instances from field-data.

        Parameters
        ----------
        entry : dict
        draft_authority : :class:`.DraftAuthority`

        Returns
        -------
        list
            A list of :class:`.DraftAuthorityLinkedData` instances.
        """

        _cast = lambda datum: DraftAuthorityLinkedData.objects.create(
            name = datum[0].upper(),
            value = datum[1],
            authority = draft_authority,
            part_of = draft_authority.part_of,
        )
        return map(_cast, entry.get('linkeddata', []))

    def generate_draftcitation(self, entry, accession):
        """
        Generate a new :class:`.DraftCitation` using the field-data in ``entry``.

        Parameters
        ----------
        entry : dict
        accession : :class:`.ImportAcession`

        Returns
        -------
        :class:`.DraftCitation`
        """

        draft_citation_data = {
            'part_of': accession,
        }
        draft_citation_data.update(dict(map(
            lambda key: (key, IngestManager._get(entry, key)), CITATION_FIELDS)
        ))

        draft_citation_data.update(IngestManager._get_pages_data(entry))
        draft_citation_data.update(IngestManager._get_dtype(entry))
        part_of_data = IngestManager._get(entry, 'part_of')

        if draft_citation_data.get('type_controlled') == DraftCitation.BOOK:
            if part_of_data:
                draft_citation_data['book_series'] = part_of_data.get('title')
        return self._update_or_create_draft_citation(draft_citation_data, entry.get('linkeddata'), part_of_data, entry)

    @staticmethod
    def _find_mapped_authority(label, ident):
        """
        Attempt to find an existing :class:`.Authority` using the lookup
        ``SUBJECT_ID_MAP``.
        """
        try:    # ident should be an int; otherwise we're barking up the wrong tree.
            pk = SUBJECT_ID_MAP.get(int(ident), None)
        except (TypeError, ValueError):
            return
        if pk:
            try:
                return Authority.objects.get(pk=pk)
            except Authority.DoesNotExist:
                return

    @staticmethod
    def _find_encoded_authority(label, ident):
        """
        Attempt to find an existing :class:`.Authority` using an equals-encoded
        classification code.
        """
        if not label.startswith('='):
            return

        # * Parse the string: "=340-140=" -> 340, 140
        m = re.match('=([0-9]+)-([0-9]+)=', label)

        # Invert the values: 340, 140 -> 140, 340
        lookup = '-'.join(m.groups()[::-1]) if m else label.replace('=', '').strip()

        # Search for an Authority with that classification_code: "140-340".
        # .first() will return None if no matching Authority is found.
        return Authority.objects.filter(classification_code=lookup).first()

    @staticmethod
    def _find_explicit_authority(label, ident):
        """
        Attempt to find an existing :class:`.Authority` using an explicit
        identifier.
        """

        # There may be typos.
        label = label.strip() if label else ''
        ident = ident.strip() if ident else ''

        if not ident.startswith('C') and not label.startswith('C'):
            return    # Neither label nor ident contain a pk identifier.

        for value in [label, ident]:
            try:
                return Authority.objects.get(pk=value)
            except Authority.DoesNotExist:
                continue
        return    # Nothing found.


    # These functions can be used to find existing Authority records. The second
    #  element of each tuple is (optionally) a value for ACRelation.type_controlled
    #  that should be enforced for this record (i.e. it should override any other
    #  explicit value).
    SUBJECT_FINDERS = [
        (_find_mapped_authority.__func__, ACRelation.SUBJECT),
        (_find_encoded_authority.__func__, ACRelation.CATEGORY),
        (_find_explicit_authority.__func__, ACRelation.SUBJECT),
    ]

    @staticmethod
    def check_for_authority_reference(label, ident, resolvers=SUBJECT_FINDERS):
        """
        Check datum for a reference to an existing :class:`.Authority` using the
        functions in ``resolvers``.

        Parameters
        ----------
        datum : tuple
        resolvers : list
            Must contain callables that accepts two arguments, and return

        Returns
        -------

        """
        candidate = None
        for _func, relation_type in resolvers:
            candidate = _func(label, ident)
            if candidate:
                break
        return candidate, relation_type

    @staticmethod
    def generate_subject_acrelations(entry, draft_citation):
        authority_type = Authority.CONCEPT

        def _cast(datum):
            label, ident = datum
            authority, acrelation_type = IngestManager.check_for_authority_reference(label, ident)

            # Usually we want to preserve the label as it appeared in the
            #  original data. If explicit mappings are used, however, we want
            #  to display the name of the matched authority rather than the
            #  code in the data.
            if label and authority and (label.startswith('=') or label.startswith('C')):
                label = authority.name

            draft_authority = DraftAuthority.objects.create(
                name=label,
                type_controlled=authority_type,
                part_of=draft_citation.part_of,
                processed=True if authority else False
            )
            if authority:
                IngestManager.resolve(draft_authority, authority)

            draft_acrelation = DraftACRelation.objects.create(**{
                'authority': draft_authority,
                'citation': draft_citation,
                'part_of': draft_citation.part_of,
                'type_controlled': acrelation_type
            })
            return draft_authority, draft_acrelation
        return map(_cast, list(set(entry.get('subjects', []))))

    @staticmethod
    def generate_publisher_acrelations(entry, draft_citation):
        # ('publisher', Authority.PUBLISHER, ACRelation.PUBLISHER)
        def _cast(datum):
            draft_authority = DraftAuthority.objects.create(
                name = datum,
                type_controlled = Authority.INSTITUTION,
                part_of = draft_citation.part_of,
            )
            draft_acrelation = DraftACRelation.objects.create(
                type_controlled = ACRelation.PUBLISHER,
                citation = draft_citation,
                authority = draft_authority,
                part_of = draft_citation.part_of,
            )
            return draft_authority, draft_acrelation
        return map(_cast, entry.get('publisher', []))

    @staticmethod
    def generate_generic_acrelations(entry, field, draft_citation, authority_type,
                                    acrelation_type):
        """
        Generate new :class:`.DraftAuthority` and :class:`.DraftACRelation`
        instances from field-data.

        Parameters
        ----------
        entry : dict
        field : str
            Name of the field in ``entry`` containing authority data.
        draft_citation : :class:`.DraftCitation`
        authority_type : str
            Must be a valid value for :prop:`.DraftAuthority.type_controlled`\.
        acrelation_type : str
            Must be a valid value for :prop:`.DraftACRelation.type_controlled`\.

        Returns
        -------
        list
            Items are (:class:`.DraftAuthority`\, :class:`.DraftACRelation`) tuples.

        """
        def _cast(datum):
            instance_data = {k: datum.get(k) for k in AUTHORITY_FIELDS}
            instance_data.update({
                'type_controlled': authority_type,
                'part_of': draft_citation.part_of
            })
            draft_authority = DraftAuthority.objects.create(**instance_data)

            # Extra data about the authority instance may be included in the
            #  ``name`` field.
            extra = IngestManager.find_extra_data(instance_data.get('name', ''))
            if extra:
                _apply = IngestManager.apply_extra_data(extra)
                draft_authority = _apply(draft_authority)

            draft_acrelation = DraftACRelation.objects.create(**{
                'authority': draft_authority,
                'citation': draft_citation,
                'part_of': draft_citation.part_of,
                'type_controlled': acrelation_type
            })
            return draft_authority, draft_acrelation
        return map(_cast, entry.get(field, []))

    def _related_citation(self, datum, draft_citation, ccrelation_type):
        # We used handle_name to process reviewed works, so this looks odd.
        identifier = datum.get('name', '').strip()
        ldata = datum.get('linkeddata', None)
        if not identifier and ldata:
                identifier = ldata[0][1]
        if not identifier:
            return None, None

        # This may refer to a Book that we are adding in this accession.
        draft_altcitation = self.draft_citation_map.get(identifier, None)

        # Sometimes explicit Citation IDs are used.
        if not draft_altcitation:
            reviewed_citation = None
            if identifier.startswith('CBB'):
                try:
                    reviewed_citation = Citation.objects.get(pk=identifier)
                except Citation.DoesNotExist:
                    pass

            # In other cases, the identifier is an ISBN; query by LinkedData.
            if not reviewed_citation and identifier:
                linkeddata = LinkedData.objects.filter(
                    type_controlled__name__icontains = 'isbn',
                    universal_resource_name = identifier).first()
                if linkeddata:
                    reviewed_citation = linkeddata.subject

            if reviewed_citation:
                # We have a Citation, but need a DraftCitation so that we can
                #  create a DraftCCRelation.
                draft_altcitation = self._update_or_create_draft_citation({
                    'title': reviewed_citation.title,
                    'type_controlled': reviewed_citation.type_controlled,
                    'part_of': draft_citation.part_of,
                }, ldata, None)
                # draft_altcitation = DraftCitation.objects.create(
                #
                # )

                # This DraftCitation is already resolved, since we have
                #  identified the record of interest in the production
                #  database.
                IngestManager.resolve(draft_altcitation, reviewed_citation)

        if not draft_altcitation:
            if 'title' not in datum:
                return None, None
            # try:
            #     self._unique_or_complain(datum)
            # except EntryNotUnique:
            #     return None, None
            title = datum.get('title')
            draft_altcitation = None
            for book in self.draft_citation_map.values():
                if book.title == title:
                    draft_altcitation = book

                    break
            if not draft_altcitation:
                draft_altcitation = self._update_or_create_draft_citation({
                    'title': title,
                    'type_controlled': IngestManager._get_dtype(datum, Citation.BOOK)['type_controlled'],
                    'part_of': draft_citation.part_of
                }, ldata, None, datum)
                # draft_altcitation = DraftCitation.objects.create(
                #
                # )
                IngestManager.generate_citation_linkeddata(datum, draft_altcitation)

        draft_ccrelation = DraftCCRelation.objects.create(
            subject = draft_altcitation,
            object = draft_citation,
            type_controlled = ccrelation_type,
            part_of = draft_citation.part_of
        )
        return draft_altcitation, draft_ccrelation

    def generate_book_chapter_relations(self, entry, draft_citation):
        """
        Generate :class:`.DraftCCRelation` instances specifically for book chapters.

        If a containing book is found, then ``draft_citation`` will be re-typed as a
        Chapter.

        Attempts to match reviewed works against (1) citations in this ingest batch,
        (2) citations with matching IDs, and (3) citations with matching linked
        data.
        """
        _is_a_book = lambda datum: IngestManager._get_dtype(datum)['type_controlled'] == DraftCitation.BOOK
        data = [datum for datum in entry.get('part_of', []) if _is_a_book(datum)]
        if not data:
            return []

        draft_citation.type_controlled = DraftCitation.CHAPTER
        draft_citation.save()
        ctype = DraftCCRelation.INCLUDES_CHAPTER
        _cast = lambda datum: self._related_citation(datum, draft_citation, ctype)
        return [result for result in map(_cast, data) if result[0] and result[1]]

    def generate_reviewed_works_relations(self, entry, draft_citation):
        """
        Generate :class:`.DraftCCRelation` instances specifically for reviews.

        If reviews are found, then ``draft_citation`` will be re-typed as a
        Review.

        Attempts to match reviewed works against (1) citations in this ingest batch,
        (2) citations with matching IDs, and (3) citations with matching linked
        data.
        """
        data = entry.get('reviewed_works', [])
        if data:    # This is a Review, regardless of what Zotero might way.
            draft_citation.type_controlled = DraftCitation.REVIEW
            draft_citation.save()

        ctype = DraftCCRelation.REVIEWED_BY
        _cast = lambda datum: self._related_citation(datum, draft_citation, ctype)
        return [result for result in map(_cast, data) if result[0] and result[1]]

    @staticmethod
    def generate_part_of_relations(entry, draft_citation):
        """
        Generate :class:`.DraftACRelation`\s based on "part of" entries in the data.

        Skips chapter and review relations.
        """
        data = entry.get('part_of', [])
        def _cast(datum):
            _type = IngestManager._get_dtype(datum)['type_controlled']
            if _type == DraftCitation.BOOK:
                return None, None
            else:
                if IngestManager._get(datum, 'type_controlled').lower() == 'journal':
                    _type = Authority.SERIAL_PUBLICATION
                    _rel_type = ACRelation.PERIODICAL
                elif IngestManager._get(datum, 'type_controlled').lower() == 'series':
                    _type = Authority.SERIAL_PUBLICATION
                    _rel_type = ACRelation.BOOK_SERIES
                else:
                    return None, None

                # Per ISISCB-734, DraftAuthorities that are the target of a
                #  Book Series relation should be processed by default.
                draft_authority = DraftAuthority.objects.create(
                    name = IngestManager._get(datum, 'title'),
                    type_controlled = _type,
                    part_of = draft_citation.part_of,
                    processed = _rel_type == ACRelation.BOOK_SERIES
                )
                _linkeddata = IngestManager.generate_authority_linkeddata(datum, draft_authority)

                draft_acrelation = DraftACRelation.objects.create(
                    authority = draft_authority,
                    citation = draft_citation,
                    type_controlled = _rel_type,
                    part_of = draft_citation.part_of,
                )
                return draft_authority, draft_acrelation
            return None, None
        return [result for result in map(_cast, data) if result[0] and result[1]]

    @staticmethod
    def generate_authorities_and_relations(entry, accession, draft_citation):
        """
        Generate new :class:`.DraftAuthority` instances and corresponding
        :class:`.DraftACRelation`\s to ``draft_citation``.

        Parameters
        ----------
        entry : dict
        accession : :class:`.ImportAccession`
        draft_citation : :class:`.DraftCitation`

        Returns
        -------
        tuple
        """

        # Build DraftAuthority and DraftACRelation.
        authorities, acrelations = process_authorities(paper, instance)
        for acrelation in acrelations:
            acrelation.citation = draftCitation
            acrelation.save()

        # Linked Data for both the Citation and Authorities.
        linkedData = process_linkeddata(paper, instance)
        for ldEntry in linkedData:
            if type(ldEntry) is DraftCitationLinkedData:
                ldEntry.citation = draftCitation
                ldEntry.save()
            elif type(ldEntry) is DraftAuthorityLinkedData:
                for authority in authorities:
                    if authority.type_controlled == 'SE':
                        ldEntry.authority = authority
                        ldEntry.save()

        # Build DraftAttributes.
        attributes = process_attributes(paper, instance)
        for attribute in attributes:
            attribute.citation = draftCitation
            attribute.save()

        draftCitation.save()
        return draftCitation, paper

    def process_entry(self, entry, accession):
        draft_citation = self.generate_draftcitation(entry, self.accession)

        acrelations = IngestManager.generate_subject_acrelations(entry, draft_citation)
        for field, authority_type, acrelation_type in GENERIC_ACRELATIONS:
            if draft_citation.type_controlled == DraftCitation.BOOK and field == 'part_of':
                continue
            acrelations += IngestManager.generate_generic_acrelations(
                entry, field, draft_citation, authority_type, acrelation_type)
        acrelations += IngestManager.generate_publisher_acrelations(
            entry, draft_citation)
        IngestManager.generate_part_of_relations(entry, draft_citation)
        return draft_citation

    def process(self):
        for entry in self.parser:
            draft_citation = self.process_entry(entry, self.accession)
            linkeddata = IngestManager.generate_citation_linkeddata(entry, draft_citation)
            self.draft_citation_map[draft_citation.id] = draft_citation
            for linkeddatum in linkeddata:
                self.draft_citation_map[linkeddatum.value] = draft_citation
            self.draft_citations.append((entry, draft_citation))

        for entry, draft_citation in self.draft_citations:
            self.generate_reviewed_works_relations(entry, draft_citation)
            self.generate_book_chapter_relations(entry, draft_citation)
        self.accession.refresh_from_db()
        return self.accession.draftcitation_set.all()


def process(parser, accession):
    return IngestManager(parser, accession).process()
