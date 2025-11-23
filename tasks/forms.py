# apps/tasks/forms.py
from django import forms


class TaskRatingForm(forms.Form):
    STAR_CHOICES = [
        (5, "5 Stars"),
        (4, "4 Stars"),
        (3, "3 Stars"),
        (2, "2 Stars"),
        (1, "1 Star"),
    ]

    rating = forms.TypedChoiceField(
        choices=STAR_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="Rate this task",
    )
