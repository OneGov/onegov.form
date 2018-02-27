from onegov.core.orm import Base
from onegov.core.orm.mixins import TimestampMixin
from onegov.core.orm.types import UUID
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.orm import relationship
from uuid import uuid4


daterange = Column(quoted_name('DATERANGE("start", "end")', quote=False))


class FormRegistrationWindow(Base, TimestampMixin):
    """ Defines a registration window during which a form definition
    may be used to create submissions.

    Submissions created thusly are attached to the currently active
    registration window.

    Registration windows may not overlap.

    """

    __tablename__ = 'registration_windows'

    #: the public id of the registraiton window
    id = Column(UUID, primary_key=True, default=uuid4)

    #: the name of the form to which this registration window belongs
    name = Column(Text, ForeignKey("forms.name"), nullable=False)

    #: true if the registration window is enabled
    enabled = Column(Boolean, nullable=False, default=True)

    #: the start date of the window
    start = Column(Date, nullable=False)

    #: the end date of the window
    end = Column(Date, nullable=False)

    #: the timezone of the window
    timezone = Column(Text, nullable=False, default='Europe/Zurich')

    #: the number of spots (None => unlimited)
    limit = Column(Integer, nullable=True)

    #: enable an overflow of submissions
    overflow = Column(Boolean, nullable=False, default=True)

    #: submissions linked to this
    submissions = relationship('FormSubmission', backref='registration_window')

    __table_args__ = (

        # ensures that there are no overlapping date ranges within one form
        ExcludeConstraint(
            (name, '='), (daterange, '&&'),
            name='no_overlapping_registration_windows',
            using='gist'
        ),

        # ensures that there are no adjacent date ranges
        # (end on the same day as next start)
        ExcludeConstraint(
            (name, '='), (daterange, '-|-'),
            name='no_adjacent_registration_windows',
            using='gist'
        ),

        # ensures that start <= end
        CheckConstraint(
            '"start" <= "end"',
            name='start_smaller_than_end'
        ),
    )
