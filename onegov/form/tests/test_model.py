import pytest

from datetime import date
from onegov.form import FormCollection, FormExtension
from sqlalchemy.exc import IntegrityError
from webob.multidict import MultiDict
from wtforms import ValidationError


def test_has_submissions(session):
    collection = FormCollection(session)
    form = collection.definitions.add('Newsletter', definition="E-Mail = @@@")

    assert not form.has_submissions()

    data = MultiDict([
        ('e_mail', 'test@example.org'),
    ])

    collection.submissions.add(
        'newsletter', form.form_class(data), state='complete')

    assert not form.has_submissions(with_state='pending')
    assert form.has_submissions(with_state='complete')
    assert form.has_submissions()


def test_form_extensions(session):
    collection = FormCollection(session)

    members = collection.definitions.add('Members', definition="E-Mail = @@@")

    class CorporateOnly(object):

        def validate_e_mail(self, value):
            # note, you probably don't want to do this in a real world
            # project as the name of the e-mail field might change and
            # the validation would not be triggered!
            if not value.data.endswith('seantis.ch'):
                raise ValidationError("Only seantis.ch e-mails are allowed")

    class CorporateOnlyExtension(FormExtension, name='corporate-emails-only'):

        def create(self):
            class ExtendedForm(self.form_class, CorporateOnly):
                pass

            return ExtendedForm

    members.meta['extensions'] = ['corporate-emails-only']
    assert issubclass(members.form_class, CorporateOnly)

    session.flush()

    # the validation should fail here
    data = MultiDict([
        ('e_mail', 'test@example.org'),
    ])

    form = members.form_class(data)
    form.validate()
    assert form.errors

    with pytest.raises(AssertionError) as e:
        collection.submissions.add('newsletter', form, state='complete')

    assert "the given form doesn't validate" in str(e)

    # now it should work
    data = MultiDict([
        ('e_mail', 'test@seantis.ch'),
    ])

    form = members.form_class(data)
    form.validate()
    assert not form.errors

    # the extensions are carried over to the submission
    submission = collection.submissions.add(
        'members', form, state='complete')
    assert issubclass(submission.form_class, CorporateOnly)


def test_registration_window_adjacent(session):
    forms = FormCollection(session)

    summer = forms.definitions.add('Summercamp', definition="E-Mail = @@@")
    winter = forms.definitions.add('Witnercamp', definition="E-Mail = @@@")

    summer.add_registration_window(date(2017, 4, 1), date(2017, 6, 30))
    summer.add_registration_window(date(2018, 4, 1), date(2018, 6, 30))

    assert len(summer.registration_windows) == 2

    winter.add_registration_window(date(2017, 4, 1), date(2017, 6, 30))
    winter.add_registration_window(date(2018, 4, 1), date(2018, 6, 30))

    assert len(winter.registration_windows) == 2

    # no overlap -> different forms
    session.flush()

    # adjacent, fails
    summer.add_registration_window(date(2017, 1, 1), date(2017, 4, 1))

    with pytest.raises(IntegrityError) as e:
        session.flush()

    assert 'no_adjacent_registration_windows' in str(e)


def test_registration_window_overlaps(session):
    forms = FormCollection(session)

    summer = forms.definitions.add('Summercamp', definition="E-Mail = @@@")
    summer.add_registration_window(date(2017, 4, 1), date(2017, 6, 30))

    assert len(summer.registration_windows) == 1

    # no overlap -> different forms
    session.flush()

    # overlapping, fails
    summer.add_registration_window(date(2017, 1, 1), date(2017, 4, 2))

    with pytest.raises(IntegrityError) as e:
        session.flush()

    assert 'no_overlapping_registration_windows' in str(e)


def test_registration_window_end_before_start(session):
    camp = FormCollection(session).definitions.add(
        'Camp', definition="E-Mail = @@@")

    camp.add_registration_window(date(2018, 1, 1), date(2017, 1, 1))

    with pytest.raises(IntegrityError) as e:
        session.flush()

    assert 'start_smaller_than_end' in str(e)
